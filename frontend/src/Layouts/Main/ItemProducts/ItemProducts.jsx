import React, { useState, useEffect } from 'react';
import classNames from 'classnames/bind';
import styles from './ItemProducts.module.scss';

import img1 from './img/items1.jpg';
import img2 from './img/items2.jpg';
import img3 from './img/items3.jpg';
import img4 from './img/items4.jpeg';
import { handleImageFallback, resolveImageUrl } from '../../../utils/image';

import { Link, useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCartPlus, faHeart } from '@fortawesome/free-solid-svg-icons';
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
import { cartQuantityForProduct, isProductPurchasable, pickPurchasableVariant, productStock } from '../../../utils/stock';
import { fetchCatalogPromotions } from '../../../api/catalogApi';

const cx = classNames.bind(styles);

const defaultProducts = [
    { img: img1, name: 'Son' },
    { img: img2, name: 'Giày' },
    { img: img3, name: 'Nến Thơm' },
    { img: img4, name: 'Nước Hoa' },
];

const VISIBLE_COUNT = 4;

function ItemProducts({ dataProducts, defaultItems }) {
    const isDynamic = Array.isArray(dataProducts) && dataProducts.length > 0;
    const fallbackList = Array.isArray(defaultItems) && defaultItems.length > 0 ? defaultItems : defaultProducts;

    const productsToShow = isDynamic ? dataProducts : fallbackList;

    const [currentIndex, setCurrentIndex] = useState(0);
    const totalPages = Math.ceil(productsToShow.length / VISIBLE_COUNT) || 1;

    const dispatch = useDispatch();
    const cartItems = useSelector((state) => state.cart);
    const navigate = useNavigate();
    const [favoriteProductIds, setFavoriteProductIds] = useState(new Set());
    const [notice, setNotice] = useState(null);
    const [promotions, setPromotions] = useState([]);

    const showNotice = (message, type = 'success') => {
        setNotice({ message, type });
        window.clearTimeout(showNotice.timeoutId);
        showNotice.timeoutId = window.setTimeout(() => setNotice(null), 2600);
    };

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
            showNotice('Thêm vào giỏ hàng thành công!');
        } catch (err) {
            showNotice('Bạn cần đăng nhập để thêm sản phẩm vào giỏ hàng!', 'error');
            navigate('/login');
        }
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

    const handlePrev = () => {
        setCurrentIndex((prev) => (prev - 1 >= 0 ? prev - 1 : totalPages - 1));
    };

    const handleNext = () => {
        setCurrentIndex((prev) => (prev + 1 < totalPages ? prev + 1 : 0));
    };

    let val = 100;
    if (productsToShow.length > 4 && productsToShow.length === 12) {
        val = 35;
    } else if (productsToShow.length > 4) {
        val = 100 - productsToShow.length * 5;
    } else {
        val = 100;
    }

    return (
        <div className={cx('wrapper')}>
            {notice && <div className={cx('notice', notice.type === 'error' && 'notice-error')}>{notice.message}</div>}

            <button className={cx('arrow', 'left')} onClick={handlePrev}>
                &#8592;
            </button>

            <div className={cx('slider')}>
                <div
                    className={cx('slider-inner')}
                    style={{
                        transform: `translateX(-${currentIndex * 100}%)`,
                        width: `${(val / VISIBLE_COUNT) * productsToShow.length}%`,
                    }}
                >
                    {productsToShow.map((product, idx) => {
                        const isReal = !!product.id;
                        const productId = isReal ? product.id : `fallback-${idx}`;
                        const name = isReal ? product.nameProducts : product.name;
                        const img = isReal ? resolveImageUrl(product.img) : product.img;

                        let canPurchase = false;
                        let canAddToCart = false;
                        let originalPrice = null;
                        let hasDiscount = false;
                        let discountPercent = 0;
                        let applicable = [];

                        if (isReal) {
                            const selectedVariant = pickPurchasableVariant(product);
                            const totalStock = productStock(product, selectedVariant);
                            canPurchase = isProductPurchasable(product, selectedVariant);
                            const quantityInCart = cartQuantityForProduct(cartItems, product?.id);
                            canAddToCart = canPurchase && quantityInCart < totalStock;

                            originalPrice = product.price && (typeof product.price === 'object' ? product.price.price : product.price);
                            const currentPrice = product.priceNew;
                            hasDiscount = originalPrice && currentPrice && Number(currentPrice) < Number(originalPrice);
                            if (hasDiscount) {
                                discountPercent = Math.round(((originalPrice - currentPrice) / originalPrice) * 100);
                            }

                            const productCategoryIds = product.categories?.map(c => Number(c.id)) || [];
                            applicable = promotions.filter(promo => {
                                const pIds = promo.product_ids || [];
                                const cIds = promo.category_ids || [];
                                if (pIds.length === 0 && cIds.length === 0) {
                                    return true;
                                }
                                const matchesProduct = pIds.includes(Number(product.id));
                                const matchesCategory = productCategoryIds.some(catId => cIds.includes(catId));
                                return matchesProduct || matchesCategory;
                            });
                        }

                        return (
                            <div key={productId} className={cx('row-product')}>
                                {isReal ? (
                                    <>
                                        <div className={cx('social-icon')}>
                                            <button
                                                type="button"
                                                className={cx('cart-button', !canAddToCart && 'cart-button-disabled')}
                                                onClick={() => handleAddProduct(product)}
                                                disabled={!canAddToCart}
                                                title={canPurchase ? 'Thêm vào giỏ hàng' : 'Sản phẩm không còn hàng'}
                                                aria-label={canPurchase ? 'Thêm vào giỏ hàng' : 'Sản phẩm không còn hàng'}
                                            >
                                                <FontAwesomeIcon icon={faCartPlus} />
                                            </button>
                                            <button
                                                type="button"
                                                className={cx('favorite-button', favoriteProductIds.has(Number(product.id)) && 'favorite-active')}
                                                onClick={() => handleToggleFavorite(product)}
                                                aria-label={favoriteProductIds.has(Number(product.id)) ? 'Bỏ yêu thích' : 'Thêm vào yêu thích'}
                                            >
                                                <FontAwesomeIcon icon={faHeart} />
                                            </button>
                                        </div>
                                        {!canPurchase && <span className={cx('stock-badge')}>Hết hàng</span>}
                                        {hasDiscount && (
                                            <span className={cx('discount-badge', !canPurchase && 'discount-badge-stacked')}>
                                                -{discountPercent}%
                                            </span>
                                        )}
                                        {favoriteProductIds.has(Number(product.id)) && (
                                            <span className={cx('favorite-badge')} aria-label="Đã yêu thích">
                                                <FontAwesomeIcon icon={faHeart} />
                                            </span>
                                        )}
                                        <Link className={cx('product-image-link')} to={`/prodetail/${product.id}`}>
                                            <img id={cx('img-item')} src={img} alt={name} onError={handleImageFallback} />
                                        </Link>
                                        <div className={cx('product-info')}>
                                            <Link className={cx('product-name-link')} to={`/prodetail/${product.id}`}>
                                                <span>{name}</span>
                                            </Link>
                                            <div className={cx('price-container')}>
                                                <span className={cx('product-price')}>{formatVndFromDb(product.priceNew)}</span>
                                                {hasDiscount && (
                                                    <span className={cx('original-price')}>{formatVndFromDb(originalPrice)}</span>
                                                )}
                                            </div>
                                            {product.price?.vat != null && Number(product.price.vat) > 0 && (
                                                <div className={cx('vat-info')} style={{ fontSize: '11px', color: '#888', marginTop: '2px', textAlign: 'center' }}>
                                                    Chưa bao gồm {product.price.vat}% VAT
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
                                    </>
                                ) : (
                                    <>
                                        <div className={cx('social-icon')}>
                                            <button
                                                type="button"
                                                className={cx('cart-button')}
                                                onClick={() => navigate('/login')}
                                                title="Đăng nhập để thêm vào giỏ"
                                            >
                                                <FontAwesomeIcon icon={faCartPlus} />
                                            </button>
                                            <button
                                                type="button"
                                                className={cx('favorite-button')}
                                                onClick={() => navigate('/login')}
                                                title="Đăng nhập để yêu thích"
                                            >
                                                <FontAwesomeIcon icon={faHeart} />
                                            </button>
                                        </div>
                                        <div className={cx('product-image-link')} onClick={() => navigate('/login')}>
                                            <img id={cx('img-item')} src={img} alt={name} onError={handleImageFallback} />
                                        </div>
                                        <div className={cx('product-info')} onClick={() => navigate('/login')}>
                                            <span className={cx('product-name-link')}>
                                                <span>{name}</span>
                                            </span>
                                        </div>
                                    </>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            <button className={cx('arrow', 'right')} onClick={handleNext}>
                &#8594;
            </button>
        </div>
    );
}

export default ItemProducts;
