import React, { useEffect, useState } from 'react';
import classNames from 'classnames/bind';
import { Heart, ShoppingCart, Trash2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';

import Footer from '../../Layouts/Footer/Footer';
import Header from '../../Layouts/Header/Header';
import Banner from '../Layouts/Banner/Banner';
import EmptyState from '../../components/EmptyState/EmptyState';
import ProductCardSkeleton from '../../components/Skeleton/ProductCardSkeleton';
import { fetchCatalogProduct } from '../../api/catalogApi';
import {
    fetchDefaultWishlist,
    removeProductFromDefaultWishlist,
} from '../../api/wishlistApi';
import { addProduct } from '../../redux/actions';
import { handleImageFallback, resolveImageUrl } from '../../utils/image';
import { formatVndFromDb } from '../../utils/price';
import { titleOf } from '../../utils/productDisplay';
import styles from './Wishlist.module.scss';

const cx = classNames.bind(styles);

function imageOf(product, fallback = '') {
    return resolveImageUrl(product?.image_url || product?.image_urls?.[0] || product?.img || fallback);
}

function priceOf(product) {
    return product?.price?.effective_price ?? product?.effective_price ?? product?.price?.price ?? product?.price ?? product?.priceNew ?? 0;
}

function productIdOf(item) {
    return item.product_id ?? item.productId;
}

function selectedVariantOf(product, item) {
    const wishlistVariantId = item.product_variant_id ?? item.productVariantId;
    const variants = product?.variants || [];
    return (
        variants.find((variant) => String(variant.id) === String(wishlistVariantId)) ||
        variants.find((variant) => variant.available && variant.active && Number(variant.inventory_count ?? 0) > 0) ||
        variants[0]
    );
}

function stockOf(product, item) {
    const selectedVariant = selectedVariantOf(product, item);
    return Number(selectedVariant?.inventory_count ?? product?.total_stock ?? product?.quantityPro ?? 0);
}

function isProductAvailable(product, item) {
    if (!product) return true;
    const selectedVariant = selectedVariantOf(product, item);
    const totalStock = stockOf(product, item);
    return Boolean(product?.available ?? totalStock > 0) && (!selectedVariant || selectedVariant.available !== false) && totalStock > 0;
}

function Wishlist() {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const [items, setItems] = useState([]);
    const [productDetails, setProductDetails] = useState({});
    const [loading, setLoading] = useState(true);
    const [addingProductId, setAddingProductId] = useState(null);
    const [notice, setNotice] = useState(null);

    const showNotice = (message, type = 'success') => {
        setNotice({ message, type });
        window.clearTimeout(showNotice.timeoutId);
        showNotice.timeoutId = window.setTimeout(() => setNotice(null), 2600);
    };

    useEffect(() => {
        loadWishlist();
    }, []);

    const loadWishlist = async () => {
        try {
            setLoading(true);
            const wishlist = await fetchDefaultWishlist();
            const nextItems = wishlist?.items || [];
            setItems(nextItems);
            await loadProductDetails(nextItems);
        } catch {
            showNotice('Bạn cần đăng nhập để xem danh sách yêu thích.', 'error');
            navigate('/login');
        } finally {
            setLoading(false);
        }
    };

    const loadProductDetails = async (wishlistItems) => {
        const productIds = Array.from(new Set(wishlistItems.map(productIdOf).filter(Boolean)));
        const entries = await Promise.all(productIds.map(async (productId) => {
            try {
                return [productId, await fetchCatalogProduct(productId)];
            } catch {
                return [productId, null];
            }
        }));
        setProductDetails(Object.fromEntries(entries));
    };

    const removeItem = async (productId) => {
        if (!productId) return;
        try {
            const wishlist = await removeProductFromDefaultWishlist(productId);
            const nextItems = wishlist?.items || [];
            setItems(nextItems);
            await loadProductDetails(nextItems);
            showNotice('Đã bỏ sản phẩm khỏi danh sách yêu thích.');
        } catch {
            showNotice('Không thể bỏ yêu thích sản phẩm.', 'error');
        }
    };

    const addItemToCart = async (item) => {
        const productId = item.product_id ?? item.productId;
        if (!productId) return;

        try {
            setAddingProductId(productId);
            const product = productDetails[productId] || await fetchCatalogProduct(productId);
            const wishlistVariantId = item.product_variant_id ?? item.productVariantId;
            const selectedVariant = selectedVariantOf(product, item);

            if (!isProductAvailable(product, item)) {
                showNotice('Sản phẩm đã hết hàng.', 'error');
                return;
            }

            dispatch(addProduct({
                ...product,
                id: product?.id || productId,
                nameProducts: titleOf(product, item.product_name_vi || item.product_name || item.productNameVi || item.productName),
                img: imageOf(product, item.image_url || item.imageUrl),
                priceNew: priceOf(product),
                productVariantId: selectedVariant?.id || wishlistVariantId || null,
                selectedVariant,
                quantity: 1,
            }));
            showNotice('Đã thêm sản phẩm vào giỏ hàng.');
        } catch {
            showNotice('Không thể thêm sản phẩm vào giỏ hàng.', 'error');
        } finally {
            setAddingProductId(null);
        }
    };

    return (
        <div className={cx('wrapper')}>
            <Header />
            <div>
                <Banner />
            </div>
            <main className={cx('inner')}>
                {notice && <div className={cx('notice', notice.type === 'error' && 'notice-error')}>{notice.message}</div>}
                <section className={cx('heading')}>
                    <div>
                        <p>Danh sách của bạn</p>
                        <h1>Sản phẩm yêu thích</h1>
                    </div>
                    <Heart className={cx('heading-icon')} size={28} />
                </section>

                {loading ? (
                    <section className={cx('grid')}>
                        {Array.from({ length: 4 }).map((_, idx) => (
                            <ProductCardSkeleton key={idx} />
                        ))}
                    </section>
                ) : !items.length ? (
                    <EmptyState
                        type="wishlist"
                        title="Chưa có sản phẩm yêu thích"
                        description="Bạn chưa lưu sản phẩm nào. Nhấn vào biểu tượng trái tim để lưu những sản phẩm bạn yêu thích!"
                        actionText="Khám phá sản phẩm"
                        actionLink="/category"
                    />
                ) : (
                    <section className={cx('grid')}>
                        {items.map((item) => {
                            const productId = productIdOf(item);
                            const title = item.product_name_vi || item.product_name || item.productNameVi || item.productName || 'Sản phẩm';
                            const image = item.image_url || item.imageUrl;
                            const product = productDetails[productId];
                            const isAvailable = isProductAvailable(product, item);
                            const addButtonDisabled = addingProductId === productId || !isAvailable;

                            const originalPrice = product?.price && (typeof product.price === 'object' ? product.price.price : product.price);
                            const currentPrice = product?.priceNew;
                            const hasDiscount = originalPrice && currentPrice && Number(currentPrice) < Number(originalPrice);
                            const discountPercent = hasDiscount ? Math.round(((originalPrice - currentPrice) / originalPrice) * 100) : 0;

                            return (
                                <article className={cx('card')} key={item.id || productId}>
                                    <Link className={cx('image')} to={`/prodetail/${productId}`}>
                                        {image ? (
                                            <img src={resolveImageUrl(image)} alt={title} onError={handleImageFallback} />
                                        ) : (
                                            <span>Chưa có ảnh</span>
                                        )}
                                        {hasDiscount && (
                                            <span className={cx('discount-badge', !isAvailable && 'discount-badge-stacked')}>
                                                -{discountPercent}%
                                            </span>
                                        )}
                                        {!isAvailable && <span className={cx('stock-badge')}>Hết hàng</span>}
                                    </Link>
                                    <div className={cx('body')}>
                                        <p>{item.brand_name || item.brandName || 'Thương hiệu đang cập nhật'}</p>
                                        <h2>{title}</h2>
                                        {product && (
                                            <div className={cx('price-container')}>
                                                <span className={cx('product-price')}>{formatVndFromDb(product.priceNew)}</span>
                                                {hasDiscount && (
                                                    <span className={cx('original-price')}>{formatVndFromDb(originalPrice)}</span>
                                                )}
                                            </div>
                                        )}
                                        <div className={cx('actions')}>
                                            <button
                                                type="button"
                                                className={cx('add-cart-button')}
                                                onClick={() => addItemToCart(item)}
                                                disabled={addButtonDisabled}
                                            >
                                                <ShoppingCart size={16} />
                                                {!isAvailable ? 'Hết hàng' : addingProductId === productId ? 'Đang thêm' : 'Thêm vào giỏ'}
                                            </button>
                                            <button type="button" onClick={() => removeItem(productId)} aria-label="Bỏ yêu thích">
                                                <Trash2 size={16} />
                                                Bỏ thích
                                            </button>
                                        </div>
                                    </div>
                                </article>
                            );
                        })}
                    </section>
                )}
            </main>
            <Footer />
        </div>
    );
}

export default Wishlist;
