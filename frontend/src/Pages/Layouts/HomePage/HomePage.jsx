import React, { useEffect, useState } from 'react';
import classNames from 'classnames/bind';
import styles from './HomePage.module.scss';
import { titleOf } from '../../../utils/productDisplay';

import { Link, useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCartPlus, faCheck, faHeart } from '@fortawesome/free-solid-svg-icons';
import { addProduct } from '../../../redux/actions';
import { useDispatch, useSelector } from 'react-redux';
import request from '../../../config/Connect';
import {
    addProductToDefaultWishlist,
    fetchDefaultWishlist,
    productIdsFromWishlist,
    removeProductFromDefaultWishlist,
} from '../../../api/wishlistApi';
import { formatVndFromDb } from '../../../utils/price';
import { handleImageFallback, resolveImageUrl } from '../../../utils/image';
import { cartQuantityForProduct, isProductPurchasable, pickPurchasableVariant, productStock } from '../../../utils/stock';
import { fetchCatalogPromotions } from '../../../api/catalogApi';
import { ProductCardSkeleton } from '../../../components/Skeleton';
import { GitCompare, Eye } from 'lucide-react';
import { useCompare } from '../../../utils/useCompare';
import { addToCompare, removeFromCompare, isInCompare, MAX_COMPARE } from '../../../utils/compare';
import CompareBar from '../../../components/CompareBar/CompareBar';
import QuickViewModal from '../../../components/QuickViewModal/QuickViewModal';
import { addRecentlyViewed } from '../../../utils/recentlyViewed';

const cx = classNames.bind(styles);

function HomePage({
    dataProducts,
    totalPages = 1,
    currentPage = 0,
    firstPage = true,
    lastPage = true,
    totalElements = 0,
    onPrevPage,
    onNextPage,
    filters,
    loading = false,
}) {
    const dispatch = useDispatch();
    const cartItems = useSelector((state) => state.cart);
    const navigate = useNavigate();
    const [favoriteProductIds, setFavoriteProductIds] = useState(new Set());
    const [notice, setNotice] = useState(null);
    const [addedProductId, setAddedProductId] = useState(null);
    const [promotions, setPromotions] = useState([]);
    const compareItems = useCompare();
    const [quickViewProduct, setQuickViewProduct] = useState(null);

    const handleQuickViewAdd = (payload) => {
        const totalStock = productStock(payload, payload.selectedVariant);
        const canPurchase = isProductPurchasable(payload, payload.selectedVariant);
        const quantityInCart = cartQuantityForProduct(cartItems, payload?.id);

        if (!canPurchase) {
            showNotice('Sản phẩm hiện không còn hàng.', 'error');
            return;
        }
        if (quantityInCart >= totalStock) {
            showNotice('Số lượng trong giỏ đã đạt tồn kho hiện có.', 'error');
            return;
        }

        request
            .get('/api/me')
            .then(() => {
                dispatch(addProduct(payload));
                setAddedProductId(payload?.id);
                showNotice('Thêm vào giỏ hàng thành công!');
                setQuickViewProduct(null);
            })
            .catch(() => {
                showNotice('Bạn cần đăng nhập để thêm sản phẩm vào giỏ hàng!', 'error');
                navigate('/login');
            });
    };

    const handleToggleCompare = (item) => {
        if (isInCompare(item.id)) {
            removeFromCompare(item.id);
            showNotice('Đã bỏ khỏi so sánh.');
            return;
        }
        const result = addToCompare(item);
        if (!result.ok && result.reason === 'max') {
            showNotice(`Chỉ so sánh tối đa ${MAX_COMPARE} sản phẩm.`, 'error');
            return;
        }
        showNotice('Đã thêm vào so sánh.');
    };

    const showNotice = (message, type = 'success') => {
        setNotice({ message, type });
        window.clearTimeout(showNotice.timeoutId);
        showNotice.timeoutId = window.setTimeout(() => setNotice(null), 2600);
    };

    useEffect(() => {
        if (addedProductId === null) return undefined;

        const timeoutId = window.setTimeout(() => setAddedProductId(null), 1600);
        return () => window.clearTimeout(timeoutId);
    }, [addedProductId]);

    useEffect(() => {
        let mounted = true;

        async function loadData() {
            try {
                const wishlist = await fetchDefaultWishlist();
                if (mounted) setFavoriteProductIds(productIdsFromWishlist(wishlist));
            } catch {
                if (mounted) setFavoriteProductIds(new Set());
            }

            try {
                const promos = await fetchCatalogPromotions();
                if (mounted) setPromotions(promos);
            } catch (err) {
                console.error('Failed to load promotions:', err);
            }
        }

        loadData();

        return () => {
            mounted = false;
        };
    }, []);

    const handleAddProduct = async (data) => {
        const selectedVariant = pickPurchasableVariant(data);
        const totalStock = productStock(data, selectedVariant);
        const canPurchase = isProductPurchasable(data, selectedVariant);
        const quantityInCart = cartQuantityForProduct(cartItems, data?.id);

        if (!canPurchase) {
            showNotice('Sản phẩm hiện không còn hàng.', 'error');
            return;
        }
        if (quantityInCart >= totalStock) {
            showNotice('Số lượng trong giỏ đã đạt tồn kho hiện có.', 'error');
            return;
        }

        try {
            await request.get('/api/me');

            dispatch(addProduct({ ...data, productVariantId: selectedVariant?.id || null, selectedVariant, quantity: 1 }));
            setAddedProductId(data?.id);
            showNotice('Thêm vào giỏ hàng thành công!');
        } catch (err) {
            showNotice('Bạn cần đăng nhập để thêm sản phẩm vào giỏ hàng!', 'error');
            navigate('/login');
        }
    };

    const getImageUrl = (imgPath) => {
        return resolveImageUrl(imgPath);
    };

    const handleToggleFavorite = async (item) => {
        const productId = Number(item?.id);
        if (!productId) return;

        const selectedVariant = item.variants?.find((variant) => variant.available && variant.active) || item.variants?.[0];
        const isFavorite = favoriteProductIds.has(productId);

        try {
            const wishlist = isFavorite
                ? await removeProductFromDefaultWishlist(productId)
                : await addProductToDefaultWishlist(productId, selectedVariant?.id || null);

            setFavoriteProductIds(productIdsFromWishlist(wishlist));
            showNotice(isFavorite ? 'Đã bỏ yêu thích sản phẩm.' : 'Đã thêm vào danh sách yêu thích.');
        } catch {
            showNotice('Bạn cần đăng nhập để lưu sản phẩm yêu thích!', 'error');
            navigate('/login');
        }
    };

    return (
        <div className={cx('wrapper')}>
            {notice && <div className={cx('notice', notice.type === 'error' && 'notice-error')}>{notice.message}</div>}

            <div className={cx('list-summary')}>
                {filters && <div className={cx('summary-filters')}>{filters}</div>}
                <div className={cx('summary-meta')}>
                    <span>{totalElements.toLocaleString()} sản phẩm</span>
                    <span>
                        Trang {currentPage + 1} / {totalPages || 1}
                    </span>
                </div>
            </div>

            {loading ? (
                <div className={cx('inner')}>
                    {Array.from({ length: 8 }).map((_, idx) => (
                        <ProductCardSkeleton key={idx} />
                    ))}
                </div>
            ) : dataProducts.length === 0 ? (
                <div className={cx('no-products')}>Không tìm thấy sản phẩm nào phù hợp</div>
            ) : (
                <div className={cx('inner')}>
                    {dataProducts.map((item) => {
                        const selectedVariant = pickPurchasableVariant(item);
                        const totalStock = productStock(item, selectedVariant);
                        const canPurchase = isProductPurchasable(item, selectedVariant);
                        const quantityInCart = cartQuantityForProduct(cartItems, item?.id);
                        const canAddToCart = canPurchase && quantityInCart < totalStock;

                        const originalPrice = item.price && (typeof item.price === 'object' ? item.price.price : item.price);
                        const currentPrice = item.priceNew;
                        const hasDiscount = originalPrice && currentPrice && Number(currentPrice) < Number(originalPrice);
                        const discountPercent = hasDiscount ? Math.round(((originalPrice - currentPrice) / originalPrice) * 100) : 0;

                        const productCategoryIds = item.categories?.map(c => Number(c.id)) || [];
                        const applicable = promotions.filter(promo => {
                            const pIds = promo.product_ids || [];
                            const cIds = promo.category_ids || [];
                            if (pIds.length === 0 && cIds.length === 0) {
                                return true;
                            }
                            const matchesProduct = pIds.includes(Number(item.id));
                            const matchesCategory = productCategoryIds.some(catId => cIds.includes(catId));
                            return matchesProduct || matchesCategory;
                        });

                        return (
                            <div key={item.id} className={cx('form-slide-products')}>
                                <div className={cx('social-icon')}>
                                    <button
                                        type="button"
                                        className={cx(
                                            'cart-button',
                                            addedProductId === item.id && 'cart-button-added',
                                            !canAddToCart && 'cart-button-disabled',
                                        )}
                                        onClick={() => handleAddProduct(item)}
                                        disabled={!canAddToCart}
                                        title={canPurchase ? 'Thêm vào giỏ hàng' : 'Sản phẩm không còn hàng'}
                                        aria-label={canPurchase ? 'Thêm vào giỏ hàng' : 'Sản phẩm không còn hàng'}
                                    >
                                        <FontAwesomeIcon icon={addedProductId === item.id ? faCheck : faCartPlus} />
                                    </button>
                                    <button
                                        type="button"
                                        className={cx('favorite-button', favoriteProductIds.has(Number(item.id)) && 'favorite-active')}
                                        onClick={() => handleToggleFavorite(item)}
                                        aria-label={favoriteProductIds.has(Number(item.id)) ? 'Bỏ yêu thích' : 'Thêm vào yêu thích'}
                                    >
                                        <FontAwesomeIcon icon={faHeart} />
                                    </button>
                                    <button
                                        type="button"
                                        className={cx('compare-button', isInCompare(item.id) && 'compare-active')}
                                        onClick={() => handleToggleCompare(item)}
                                        aria-label={isInCompare(item.id) ? 'Bỏ khỏi so sánh' : 'Thêm vào so sánh'}
                                        title={isInCompare(item.id) ? 'Bỏ khỏi so sánh' : 'So sánh'}
                                    >
                                        <GitCompare size={16} />
                                    </button>
                                    <button
                                        type="button"
                                        className={cx('quickview-button')}
                                        onClick={() => setQuickViewProduct(item)}
                                        aria-label="Xem nhanh"
                                        title="Xem nhanh"
                                    >
                                        <Eye size={16} />
                                    </button>
                                </div>
                                {!canPurchase && <span className={cx('stock-badge')}>Hết hàng</span>}
                                {hasDiscount && (
                                    <span className={cx('discount-badge', !canPurchase && 'discount-badge-stacked')}>
                                        -{discountPercent}%
                                    </span>
                                )}
                                {favoriteProductIds.has(Number(item.id)) && (
                                    <span className={cx('favorite-badge')} aria-label="Đã yêu thích">
                                        <FontAwesomeIcon icon={faHeart} />
                                    </span>
                                )}
                                <Link className={cx('product-image-link')} to={`/prodetail/${item.id}`}>
                                    <img
                                        src={getImageUrl(item.img)}
                                        alt={titleOf(item)}
                                        className={cx('product-image')}
                                        onError={handleImageFallback}
                                    />
                                </Link>
                                <div className={cx('main-slide-products')}>
                                    <h1>{titleOf(item)}</h1>
                                    <div className={cx('price-slide-products')}>
                                        <span className={cx('product-price')}>{formatVndFromDb(item.priceNew)}</span>
                                        {hasDiscount && (
                                            <span className={cx('original-price')}>{formatVndFromDb(originalPrice)}</span>
                                        )}
                                    </div>
                                    {item.price?.vat != null && Number(item.price.vat) > 0 && (
                                        <div className={cx('vat-info')} style={{ fontSize: '11px', color: '#888', marginTop: '2px', textAlign: 'center' }}>
                                            Chưa bao gồm {item.price.vat}% VAT
                                        </div>
                                    )}
                                    {applicable.length > 0 && (() => {
                                        const first = applicable[0];
                                        const rest  = applicable.slice(1);
                                        const isGreen = (p) => p.name === 'Flash Sale Cu\u1ed1i Tu\u1ea7n' || p.name === 'Khuy\u1ebfn M\u00e3i H\u00e8 2026 - Gi\u1ea3m Gi\u00e1 To\u00e0n B\u1ed9 S\u1ea3n Ph\u1ea9m';
                                        const badgeStyle = (p) => isGreen(p)
                                            ? { fontSize: '9px', backgroundColor: 'rgba(46,204,113,0.15)', color: '#27ae60', border: '1px solid #27ae60', padding: '1px 5px', borderRadius: '3px', fontWeight: 600, whiteSpace: 'nowrap', maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', display: 'inline-block' }
                                            : { fontSize: '9px', backgroundColor: 'rgba(231,76,60,0.15)',  color: '#e74c3c', border: '1px solid #e74c3c',  padding: '1px 5px', borderRadius: '3px', fontWeight: 600, whiteSpace: 'nowrap', maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', display: 'inline-block' };
                                        return (
                                            <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center' }}>
                                                <span title={first.name} style={badgeStyle(first)}>{first.name}</span>
                                                {rest.length > 0 && (
                                                    <span className={cx('promo-more-wrap')}>
                                                        <span className={cx('promo-more-pill')}>+{rest.length}</span>
                                                        <span className={cx('promo-tooltip')}>
                                                            {applicable.map((p) => (
                                                                <span key={p.id} className={cx('promo-tooltip-item', isGreen(p) ? 'promo-tooltip-green' : 'promo-tooltip-red')}>{p.name}</span>
                                                            ))}
                                                        </span>
                                                    </span>
                                                )}
                                            </div>
                                        );
                                    })()}

                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            <div className={cx('pager')}>
                <button type="button" disabled={firstPage || !onPrevPage} onClick={onPrevPage}>
                    Trước
                </button>
                <span>
                    Trang {currentPage + 1} / {totalPages || 1}
                </span>
                <button type="button" disabled={lastPage || !onNextPage} onClick={onNextPage}>
                    Sau
                </button>
            </div>

            <CompareBar />

            <QuickViewModal
                product={quickViewProduct}
                open={!!quickViewProduct}
                onClose={() => setQuickViewProduct(null)}
                onAddToCart={handleQuickViewAdd}
            />
        </div>
    );
}

export default HomePage;
