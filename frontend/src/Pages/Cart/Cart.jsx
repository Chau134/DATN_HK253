
import React, { useMemo, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import classNames from 'classnames/bind';
import styles from './Cart.module.scss';
import { titleOf } from '../../utils/productDisplay';

import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import Banner from '../Layouts/Banner/Banner';
import EmptyState from '../../components/EmptyState/EmptyState';

import { addProduct, removeProduct } from '../../redux/actions';
import { useDispatch, useSelector } from 'react-redux';

import { Bounce, ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import request, { getApiError } from '../../config/Connect';
import { fetchCatalogProduct } from '../../api/catalogApi';
import { formatVndFromDb } from '../../utils/price';
import { pickPurchasableVariant } from '../../utils/stock';
import { resolveImageUrl, handleImageFallback } from '../../utils/image';
import { Trash2, Plus, Minus } from 'lucide-react';

const cx = classNames.bind(styles);

function getCartProductId(item) {
    return item?.id || item?._id || item?.product_id || item?.productId;
}

async function resolveProductVariantId(item) {
    const currentVariantId =
        item?.productVariantId ||
        item?.product_variant_id ||
        item?.selectedVariant?.id ||
        item?.variants?.[0]?.id;

    if (currentVariantId) return currentVariantId;

    const productId = getCartProductId(item);
    if (!productId) return null;

    const product = await fetchCatalogProduct(productId);
    const variant = pickPurchasableVariant(product);
    return variant?.id || null;
}

function CartUser() {
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const cartItemsFromStore = useSelector(state => state.cart);
    const cartItems = cartItemsFromStore.length 
        ? cartItemsFromStore 
        : JSON.parse(localStorage.getItem('products') || '[]');

    // State lưu thông tin user
    const [user, setUser] = useState(null);
    const [loadingUser, setLoadingUser] = useState(true); // trạng thái load use

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const res = await request.get('/api/me');
                setUser(res.data);
            } catch (err) {
                setUser(null);
            } finally {
                setLoadingUser(false);
            }
        };
        fetchUser();
    }, []);


    // Tính tổng tiền
    const total = useMemo(() => {
        return cartItems.reduce(
            (acc, item) => acc + ((item.priceNew || 0) * (item.quantity || 1)), 
            0
        );
    }, [cartItems]);

    const handleIncreaseQuantity = (item) => {
        dispatch(addProduct({ ...item, quantity: 1 }));
    };

    const handleDecreaseQuantity = (item) => {
        if ((item.quantity || 1) > 1) {
            dispatch(addProduct({ ...item, quantity: -1 }));
        }
    };

    const handleDeleteProduct = (id) => {
        dispatch(removeProduct(id));
    };

    const handlePostCart = async () => {
        if (!user || !user.email) {
            toast.error('Ban can dang nhap !!!');
            return;
        }
        if (cartItems.length <= 0) {
            toast.error('Vui long them san pham vao gio hang !!!');
            return;
        }

        try {
            // 1. Fetch current database cart items
            const currentCartRes = await request.get('/api/cart');
            const currentItems = currentCartRes.data?.items || [];
            
            // 2. Delete all existing items in database cart to avoid quantity accumulation
            await Promise.all(currentItems.map((item) => {
                return request.delete(`/api/cart/items/${item.id}`);
            }));

            // 3. Post new items with correct quantities
            await Promise.all(cartItems.map((item) => {
                return resolveProductVariantId(item).then((productVariantId) => {
                    if (!productVariantId) {
                        throw new Error(`${titleOf(item)} chưa có biến thể để thanh toán.`);
                    }

                    return request.post('/api/cart/items', {
                        product_variant_id: productVariantId,
                        quantity: item.quantity || 1,
                    });
                });
            }));
            navigate('/checkout');
        } catch (error) {
            toast.error(getApiError(error, 'Không thể chuyển sang thanh toán'));
        }
    };

    if (cartItems.length === 0) {
        return (
            <div className={cx('wrapper')}>
                <ToastContainer transition={Bounce} icon={false} />
                <header><Header /></header>
                <div><Banner /></div>
                <main>
                    <div className={cx('inner')}>
                        <EmptyState
                            type="cart"
                            title="Giỏ hàng trống"
                            description="Bạn chưa có sản phẩm nào trong giỏ hàng. Hãy khám phá và thêm sản phẩm yêu thích!"
                            actionText="Khám phá sản phẩm"
                            actionLink="/category"
                        />
                    </div>
                </main>
                <footer><Footer /></footer>
            </div>
        );
    }

    return (
        <div className={cx('wrapper')}>
            <ToastContainer transition={Bounce} icon={false} />
            <header><Header /></header>
            <div><Banner /></div>
            <main>
                <div className={cx('inner')}>
                    <div className={cx('cart-container')}>
                        <div className={cx('cart-items')}>
                            <h2 className={cx('cart-title')}>Giỏ hàng của bạn ({cartItems.length} sản phẩm)</h2>
                            {cartItems.map((item, index) => (
                                <div key={`${item.id}-${index}`} className={cx('cart-item-card')}>
                                    <Link to={`/prodetail/${item.id}`} className={cx('item-image-link')}>
                                        <img
                                            src={resolveImageUrl(item.img)}
                                            alt={titleOf(item)}
                                            className={cx('item-image')}
                                            onError={handleImageFallback}
                                        />
                                    </Link>
                                    <div className={cx('item-details')}>
                                        <Link to={`/prodetail/${item.id}`} className={cx('item-name')}>
                                            {titleOf(item)}
                                        </Link>
                                        {item.selectedVariant && (
                                            <div className={cx('item-variant')}>
                                                {item.selectedVariant.size && <span>Size: {item.selectedVariant.size}</span>}
                                                {item.selectedVariant.color && <span>Màu: {item.selectedVariant.color}</span>}
                                            </div>
                                        )}
                                        <div className={cx('item-price')}>
                                            {formatVndFromDb(item.priceNew)}
                                        </div>
                                    </div>
                                    <div className={cx('item-actions')}>
                                        <div className={cx('quantity-controls')}>
                                            <button
                                                onClick={() => handleDecreaseQuantity(item)}
                                                className={cx('qty-btn')}
                                                aria-label="Giảm số lượng"
                                            >
                                                <Minus size={16} />
                                            </button>
                                            <span className={cx('qty-value')}>{item.quantity || 1}</span>
                                            <button
                                                onClick={() => handleIncreaseQuantity(item)}
                                                className={cx('qty-btn')}
                                                aria-label="Tăng số lượng"
                                            >
                                                <Plus size={16} />
                                            </button>
                                        </div>
                                        <div className={cx('item-total')}>
                                            {formatVndFromDb((item.priceNew || 0) * (item.quantity || 1))}
                                        </div>
                                        <button
                                            onClick={() => handleDeleteProduct(item.id)}
                                            className={cx('remove-btn')}
                                            aria-label="Xóa sản phẩm"
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                        <div className={cx('cart-summary')}>
                            <h3 className={cx('summary-title')}>Tổng đơn hàng</h3>
                            <div className={cx('summary-row')}>
                                <span>Tạm tính</span>
                                <span>{formatVndFromDb(total)}</span>
                            </div>
                            <div className={cx('summary-row')}>
                                <span>Phí vận chuyển</span>
                                <span>Miễn phí</span>
                            </div>
                            <div className={cx('summary-divider')}></div>
                            <div className={cx('summary-total')}>
                                <span>Tổng cộng</span>
                                <span className={cx('total-amount')}>{formatVndFromDb(total)}</span>
                            </div>
                            <button
                                onClick={handlePostCart}
                                disabled={loadingUser}
                                className={cx('checkout-btn')}
                            >
                                {loadingUser ? 'Đang tải...' : 'Tiến hành thanh toán'}
                            </button>
                            <Link to="/category" className={cx('continue-shopping')}>
                                Tiếp tục mua sắm
                            </Link>
                        </div>
                    </div>
                </div>
            </main>
            <footer><Footer /></footer>
        </div>
    );
}

export default CartUser;


