import classNames from 'classnames/bind';
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import styles from './ProductDetail.module.scss';

import Footer from '../../Layouts/Footer/Footer';
import Header from '../../Layouts/Header/Header';

import { faStar } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { Heart, ShoppingCart } from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import { addProduct } from '../../redux/actions';

import {
    fetchCatalogProduct,
    fetchCatalogProductReviewSummary,
    fetchCatalogProductReviews,
    fetchCatalogPromotions,
} from '../../api/catalogApi';
import {
    addProductToDefaultWishlist,
    fetchDefaultWishlist,
    productIdsFromWishlist,
    removeProductFromDefaultWishlist,
} from '../../api/wishlistApi';
import { formatCurrencyFromDb } from '../../utils/price';
import { handleImageFallback, resolveImageUrl } from '../../utils/image';
import { cartQuantityForProduct, isProductPurchasable, isVariantPurchasable, productStock } from '../../utils/stock';
import Lightbox from 'yet-another-react-lightbox';
import Zoom from 'yet-another-react-lightbox/plugins/zoom';
import Thumbnails from 'yet-another-react-lightbox/plugins/thumbnails';
import 'yet-another-react-lightbox/styles.css';
import 'yet-another-react-lightbox/plugins/thumbnails.css';
import ProductDetailSkeleton from '../../components/Skeleton/ProductDetailSkeleton';
import RecentlyViewed from '../../components/RecentlyViewed/RecentlyViewed';
import { addRecentlyViewed } from '../../utils/recentlyViewed';
import { descriptionOf, titleOf } from '../../utils/productDisplay';


const cx = classNames.bind(styles);

const FALLBACK_AVATAR = 'https://images.unsplash.com/photo-1633332755192-727a05c4013d';

function getImageUrl(imgPath) {
    return resolveImageUrl(imgPath);
}

function galleryImagesOf(product) {
    const urls = [];
    const add = (url) => {
        if (!url || typeof url !== 'string') return;
        const resolved = getImageUrl(url);
        if (resolved && !urls.includes(resolved)) {
            urls.push(resolved);
        }
    };

    add(product?.main_image || product?.mainImage);
    add(product?.image_url || product?.imageUrl);

    if (Array.isArray(product?.image_urls)) {
        product.image_urls.forEach(add);
    }

    if (Array.isArray(product?.images)) {
        product.images.forEach((image) => add(image?.image_url || image?.imageUrl || image?.url));
    }

    add(product?.img);

    return urls;
}

function getReviewText(review) {
    return review?.comment || review?.content || review?.title || '';
}

function getReviewerName(review) {
    return (
        review?.user?.display_name ||
        review?.user?.displayName ||
        review?.user?.full_name ||
        review?.user?.fullName ||
        review?.user?.email ||
        review?.userId?.fullname ||
        review?.userId?.email ||
        (review?.user_account_id ? `Người dùng #${review.user_account_id}` : 'Khách hàng')
    );
}

function getReviewerAvatar(review) {
    const avatar =
        review?.user?.avatar_url ||
        review?.user?.avatarUrl ||
        review?.avatar_url ||
        review?.avatar ||
        review?.userId?.avatar;

    if (!avatar) return FALLBACK_AVATAR;
    if (avatar.startsWith('http')) return avatar;
    return avatar;
}

function Stars({ value = 0, size = 18 }) {
    return (
        <span className={cx('stars')} aria-label={`${value.toFixed(1)} trên 5 sao`}>
            {[1, 2, 3, 4, 5].map((star) => (
                <FontAwesomeIcon
                    key={star}
                    icon={faStar}
                    className={cx(star <= Math.round(value) ? 'star-active' : 'star-muted')}
                    style={{ fontSize: size }}
                />
            ))}
        </span>
    );
}

function ProductDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const cartItems = useSelector((state) => state.cart);
    const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);

    const [product, setProduct] = useState(null);
    const [reviews, setReviews] = useState([]);
    const [summary, setSummary] = useState(null);
    const [selectedVariantId, setSelectedVariantId] = useState('');
    const [favoriteProductIds, setFavoriteProductIds] = useState(new Set());
    const [notice, setNotice] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [applicablePromotions, setApplicablePromotions] = useState([]);
    const [selectedImage, setSelectedImage] = useState('');
    const [lightboxOpen, setLightboxOpen] = useState(false);
    const [zoomOrigin, setZoomOrigin] = useState('center center');
    const [isZooming, setIsZooming] = useState(false);

    const showNotice = (message, type = 'success') => {
        setNotice({ message, type });
        window.clearTimeout(showNotice.timeoutId);
        showNotice.timeoutId = window.setTimeout(() => setNotice(null), 2600);
    };

    useEffect(() => {
        let mounted = true;

        async function loadProductDetail() {
            if (!id) return;
            setLoading(true);
            setError('');

            try {
                const [productData, reviewsResult, summaryResult, promotionsRes] = await Promise.all([
                    fetchCatalogProduct(id),
                    fetchCatalogProductReviews(id).catch(() => []),
                    fetchCatalogProductReviewSummary(id).catch(() => null),
                    fetchCatalogPromotions().catch(() => []),
                ]);

                if (!mounted) return;
                setProduct(productData);
                addRecentlyViewed(productData);
                setReviews(reviewsResult);
                setSummary(summaryResult || productData?.review_summary || null);

                // Filter applicable promotions
                const productCategoryIds = productData?.categories?.map(c => Number(c.id)) || [];
                const applicable = promotionsRes.filter(promo => {
                    const pIds = promo.product_ids || [];
                    const cIds = promo.category_ids || [];
                    if (pIds.length === 0 && cIds.length === 0) {
                        return true;
                    }
                    const matchesProduct = pIds.includes(Number(productData.id));
                    const matchesCategory = productCategoryIds.some(catId => cIds.includes(catId));
                    return matchesProduct || matchesCategory;
                });
                setApplicablePromotions(applicable);

                const variants = productData?.variants || [];
                const firstAvailable = variants.find(isVariantPurchasable) || variants[0];
                setSelectedVariantId(firstAvailable?.id ? String(firstAvailable.id) : '');
            } catch (err) {
                if (!mounted) return;
                console.error(err);
                setError('Không thể tải thông tin sản phẩm.');
            } finally {
                if (mounted) setLoading(false);
            }
        }

        loadProductDetail();

        return () => {
            mounted = false;
        };
    }, [id]);

    useEffect(() => {
        if (!isAuthenticated) {
            setFavoriteProductIds(new Set());
            return undefined;
        }

        let mounted = true;

        async function loadWishlist() {
            try {
                const wishlist = await fetchDefaultWishlist();
                if (mounted) setFavoriteProductIds(productIdsFromWishlist(wishlist));
            } catch {
                if (mounted) setFavoriteProductIds(new Set());
            }
        }

        loadWishlist();

        return () => {
            mounted = false;
        };
    }, [isAuthenticated]);

    const variants = product?.variants || [];
    const selectedVariant = variants.find((variant) => String(variant.id) === String(selectedVariantId));
    const galleryImages = useMemo(() => galleryImagesOf(product), [product]);
    const image = selectedImage || galleryImages[0] || '';
    const price = product?.price?.effective_price ?? product?.price?.price ?? product?.priceNew;
    const currency = product?.price?.currency || 'VND';
    const totalStock = productStock(product, selectedVariant);
    const isAvailable = isProductPurchasable(product, selectedVariant);
    const quantityInCart = cartQuantityForProduct(cartItems, product?.id);
    const canAddToCart = isAvailable && quantityInCart < totalStock;

    const originalPrice = product?.price && (typeof product.price === 'object' ? product.price.price : product.price);
    const hasDiscount = originalPrice && price && Number(price) < Number(originalPrice);
    const discountPercent = hasDiscount ? Math.round(((originalPrice - price) / originalPrice) * 100) : 0;

    const averageRating = useMemo(() => {
        const summaryAverage = Number(summary?.average_rating ?? summary?.averageRating ?? 0);
        if (summaryAverage > 0) return summaryAverage;

        const ratedReviews = reviews.filter((review) => Number(review?.rating) > 0);
        if (!ratedReviews.length) return 0;
        return ratedReviews.reduce((sum, review) => sum + Number(review.rating || 0), 0) / ratedReviews.length;
    }, [reviews, summary]);

    const reviewCount = Number(summary?.approved_review_count ?? summary?.review_count ?? reviews.length ?? 0);
    const isFavorite = favoriteProductIds.has(Number(product?.id));

    useEffect(() => {
        setSelectedImage(galleryImages[0] || '');
    }, [galleryImages, product?.id]);

    const handleToggleFavorite = async () => {
        if (!isAuthenticated) {
            navigate('/login');
            return;
        }

        const productId = Number(product?.id);
        if (!productId) return;

        try {
            const wishlist = isFavorite
                ? await removeProductFromDefaultWishlist(productId)
                : await addProductToDefaultWishlist(productId, selectedVariant?.id || null);

            setFavoriteProductIds(productIdsFromWishlist(wishlist));
            showNotice(isFavorite ? 'Đã xóa khỏi danh sách yêu thích.' : 'Đã thêm vào danh sách yêu thích.');
        } catch {
            showNotice('Vui lòng đăng nhập để lưu sản phẩm yêu thích.', 'error');
            navigate('/login');
        }
    };

    const handleAddProduct = () => {
        if (!isAuthenticated) {
            navigate('/login');
            return;
        }

        if (!product) return;
        if (!isAvailable) {
            showNotice('Sản phẩm này đã hết hàng.', 'error');
            return;
        }
        if (!canAddToCart) {
            showNotice('Bạn đã chọn số lượng tối đa hiện có.', 'error');
            return;
        }

        dispatch(
            addProduct({
                ...product,
                productVariantId: selectedVariant?.id || null,
                selectedVariant,
                quantity: 1,
            }),
        );
        showNotice('Đã thêm sản phẩm vào giỏ hàng!');
    };

    return (
        <div className={cx('wrapper')}>
            {notice && <div className={cx('notice', notice.type === 'error' && 'notice-error')}>{notice.message}</div>}
            <header>
                <Header />
            </header>

            <main className={cx('detail-page')}>
                {loading ? (
                    <ProductDetailSkeleton />
                ) : error ? (
                    <div className={cx('state-message')}>{error}</div>
                ) : (
                    <>
                        <section className={cx('detail-layout')}>
                            <div className={cx('detail-gallery')}>
                                {galleryImages.length > 1 && (
                                    <div className={cx('thumbnail-list')} aria-label="Danh sách ảnh sản phẩm">
                                        {galleryImages.map((galleryImage, index) => (
                                            <button
                                                key={galleryImage}
                                                type="button"
                                                className={cx('thumbnail-button', galleryImage === image && 'thumbnail-active')}
                                                onClick={() => setSelectedImage(galleryImage)}
                                                aria-label={`Xem ảnh sản phẩm ${index + 1}`}
                                            >
                                                <img src={galleryImage} alt={`${titleOf(product)} ${index + 1}`} onError={handleImageFallback} />
                                            </button>
                                        ))}
                                    </div>
                                    )}

                                <div
                                    className={cx('detail-image', isZooming && 'detail-image-zooming')}
                                    onClick={() => image && setLightboxOpen(true)}
                                    onMouseMove={(event) => {
                                        const rect = event.currentTarget.getBoundingClientRect();
                                        const x = ((event.clientX - rect.left) / rect.width) * 100;
                                        const y = ((event.clientY - rect.top) / rect.height) * 100;
                                        setZoomOrigin(`${x}% ${y}%`);
                                    }}
                                    onMouseEnter={() => setIsZooming(true)}
                                    onMouseLeave={() => setIsZooming(false)}
                                    role="button"
                                    tabIndex={0}
                                    aria-label="Phóng to ảnh sản phẩm"
                                >
                                    {image ? (
                                    <img
                                        src={image}
                                        alt={titleOf(product)}
                                        onError={handleImageFallback}
                                        style={{ transformOrigin: zoomOrigin }}
                                    />
                                    ) : (
                                    <div className={cx('image-placeholder')}>Chưa có ảnh</div>
                                )}
                                </div>
                            </div>

                            <div className={cx('detail-info')}>
                                <p className={cx('eyebrow')}>{product?.brand || product?.author || 'Sản phẩm'}</p>
                                <h2>{titleOf(product)}</h2>

                                <p className={cx('muted')}>{descriptionOf(product)}</p>
                                <div className={cx('price-area')}>
                                    <strong className={cx('price-line')}>{formatCurrencyFromDb(price, currency)}</strong>
                                    {hasDiscount && (
                                        <>
                                            <span className={cx('original-price')}>{formatCurrencyFromDb(originalPrice, currency)}</span>
                                            <span className={cx('discount-tag')}>-{discountPercent}%</span>
                                        </>
                                    )}
                                    {product?.price?.vat != null && Number(product.price.vat) > 0 && (
                                        <span className={cx('vat-tag')} style={{ fontSize: '14px', color: '#888', marginLeft: '10px' }}>
                                            (Chưa gồm {product.price.vat}% VAT)
                                        </span>
                                    )}
                                </div>

                                {variants.length > 0 && (
                                    <div className={cx('variant-field')}>
                                        <div className={cx('variant-header')}>
                                            <span className={cx('variant-label')}>Chọn kích cỡ</span>
                                            <button type="button" className={cx('size-guide')}>Hướng dẫn chọn cỡ</button>
                                        </div>
                                        <div className={cx('size-grid')}>
                                            {variants.map((variant) => {
                                                const label = variant.unified_size || variant.option_value || variant.sku_id || `#${variant.id}`;
                                                const soldOut = !isVariantPurchasable(variant);
                                                return (
                                                    <button
                                                        key={variant.id}
                                                        type="button"
                                                        className={cx('size-pill', String(variant.id) === String(selectedVariantId) && 'size-pill-active', soldOut && 'size-pill-disabled')}
                                                        onClick={() => setSelectedVariantId(String(variant.id))}
                                                        disabled={soldOut}
                                                        title={soldOut ? 'Hết hàng' : `Còn ${variant.inventory_count ?? 0} sản phẩm`}
                                                    >
                                                        {label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                <div className={cx('stock-note', !isAvailable && 'stock-note-empty')}>
                                    {isAvailable ? `Còn hàng: ${totalStock}` : 'Hết hàng'}
                                </div>

                                <div className={cx('action-row')}>
                                    <button
                                        className={cx('primary-button')}
                                        disabled={!isAvailable || (isAuthenticated && !canAddToCart)}
                                        onClick={handleAddProduct}
                                        title={isAvailable ? 'Thêm vào giỏ hàng' : 'Hết hàng'}
                                    >
                                        <ShoppingCart size={18} />
                                        {!isAvailable
                                            ? 'Hết hàng'
                                            : isAuthenticated && !canAddToCart
                                                ? 'Đã đạt số lượng tối đa'
                                                : 'Thêm vào giỏ hàng'}
                                    </button>
                                    <button type="button" className={cx('wishlist-button', isFavorite && 'wishlist-active')} onClick={handleToggleFavorite}>
                                        {isFavorite ? 'Đã yêu thích' : 'Yêu thích'}
                                        <Heart size={18} fill={isFavorite ? 'currentColor' : 'none'} />
                                    </button>
                                </div>
                            </div>
                        </section>

                        <section className={cx('detail-extra')}>
                            <div className={cx('reviews-panel')}>
                                <div className={cx('section-title')}>
                                    <span>Đánh giá</span>
                                    <small>{reviewCount} đánh giá</small>
                                </div>

                                <div className={cx('review-summary')}>
                                    <strong>{averageRating ? averageRating.toFixed(1) : '0.0'}</strong>
                                    <Stars value={averageRating} size={18} />
                                </div>

                                <div className={cx('review-cta')}>
                                    <p>Bạn đã mua sản phẩm này? Hãy chia sẻ đánh giá.</p>
                                    <button type="button" onClick={() => navigate('/order-history')}>
                                        Đánh giá sản phẩm đã mua
                                    </button>
                                </div>

                                <div className={cx('comments-user')}>
                                    {reviews.length === 0 && <p className={cx('empty-review')}>Chưa có đánh giá</p>}
                                    {reviews.map((review) => (
                                        <div className={cx('form-comment')} key={review.id || review._id}>
                                            <img src={getReviewerAvatar(review)} alt={getReviewerName(review)} />
                                            <div className={cx('comment-body')}>
                                                <div className={cx('comment-head')}>
                                                    <span>{getReviewerName(review)}</span>
                                                    <Stars value={Number(review.rating || 0)} size={15} />
                                                </div>
                                                {review.title && <strong>{review.title}</strong>}
                                                <p>{getReviewText(review) || 'Người dùng chưa để lại nhận xét.'}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </section>

                        <RecentlyViewed excludeId={product?.id} />
                    </>
                )}
            </main>

            {galleryImages.length > 0 && (
                <Lightbox
                    open={lightboxOpen}
                    close={() => setLightboxOpen(false)}
                    index={Math.max(galleryImages.indexOf(image), 0)}
                    slides={galleryImages.map((src) => ({ src }))}
                    plugins={[Zoom, Thumbnails]}
                    on={{ view: ({ index }) => setSelectedImage(galleryImages[index] || image) }}
                />
            )}

            <footer>
                <Footer />
            </footer>
        </div>
    );
}

export default ProductDetail;
