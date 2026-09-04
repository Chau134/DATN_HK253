import { useEffect, useState } from 'react';
import classNames from 'classnames/bind';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { Bounce, ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import Banner from '../Layouts/Banner/Banner';
import Loading from '../../Layouts/Loading/Loading';
import request, { getApiError } from '../../config/Connect';
import { clearCart } from '../../redux/actions';
import { formatVndFromDb } from '../../utils/price';
import styles from './Checkout.module.scss';
import { titleOf } from '../../utils/productDisplay';

const cx = classNames.bind(styles);

function Checkout() {
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const [dataCart, setDataCart] = useState({ products: [], sumPrice: 0 });
    const [checkBox, setCheckBox] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [paymentMethod, setPaymentMethod] = useState('COD');

    const [couponCodeInput, setCouponCodeInput] = useState('');
    const [appliedCouponCode, setAppliedCouponCode] = useState('');
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);
    const [previewData, setPreviewData] = useState({
        subtotal: 0,
        promotionDiscount: 0,
        couponDiscount: 0,
        totalDiscount: 0,
        total: 0,
    });
    const [availableCoupons, setAvailableCoupons] = useState([]);
    const [showCouponsDropdown, setShowCouponsDropdown] = useState(false);

    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [phoneNumber, setPhoneNumber] = useState('');
    const [email, setEmail] = useState('');
    const [province, setProvince] = useState('');
    const [addressLine1, setAddressLine1] = useState('');
    const [district, setDistrict] = useState('');
    const [ward, setWard] = useState('');
    const [savedAddressId, setSavedAddressId] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // 1. Fetch Cart
                const cartRes = await request.get('/api/cart');
                setDataCart({
                    id: cartRes.data.id,
                    products: cartRes.data.items || [],
                    sumPrice: Number(cartRes.data.subtotal || 0),
                });

                // Fetch preview
                fetchPreview(cartRes.data.id, null);

                // Fetch active coupons
                try {
                    const couponsRes = await request.get('/api/coupons');
                    setAvailableCoupons(couponsRes.data || []);
                } catch (err) {
                    console.error('Error fetching available coupons', err);
                }

                // 2. Fetch User Profile to pre-fill email
                try {
                    const meRes = await request.get('/api/me');
                    if (meRes.data?.email) {
                        setEmail(meRes.data.email);
                    }
                } catch (err) {
                    console.error('Error fetching user email', err);
                }

                // 3. Fetch Saved Addresses to pre-fill shipping details
                try {
                    const addrRes = await request.get('/api/me/addresses');
                    const addresses = addrRes.data || [];
                    if (addresses.length > 0) {
                        // Use default address or the first one available
                        const defaultAddr = addresses.find(addr => addr.is_default) || addresses[0];
                        if (defaultAddr) {
                            setSavedAddressId(defaultAddr.id);
                            setPhoneNumber(defaultAddr.phone_number || '');
                            setProvince(defaultAddr.province || defaultAddr.city || '');
                            setAddressLine1(defaultAddr.address_line1 || '');
                            setDistrict(defaultAddr.district || '');
                            setWard(defaultAddr.ward || '');
                            
                            // Parse recipient_name into firstName and lastName
                            const recipientName = defaultAddr.recipient_name || '';
                            const parts = recipientName.trim().split(' ');
                            if (parts.length > 1) {
                                setLastName(parts[0]);
                                setFirstName(parts.slice(1).join(' '));
                            } else {
                                setFirstName(recipientName);
                                setLastName('');
                            }
                        }
                    }
                } catch (err) {
                    console.error('Error fetching saved addresses', err);
                }
            } catch (error) {
                toast.error(getApiError(error, 'Bạn cần đăng nhập lại'));
                navigate('/login');
            }
        };

        fetchData();
    }, [navigate]);

    const fetchPreview = async (cartId, code) => {
        setIsLoadingPreview(true);
        try {
            const res = await request.post('/api/checkout/preview', {
                cart_id: cartId,
                coupon_code: code || null,
            });
            setPreviewData({
                subtotal: Number(res.data.subtotal_amount || 0),
                promotionDiscount: Number(res.data.promotion_discount_amount || 0),
                couponDiscount: Number(res.data.coupon_discount_amount || 0),
                totalDiscount: Number(res.data.total_discount_amount || 0),
                taxAmount: Number(res.data.tax_amount || 0),
                total: Number(res.data.total_amount || 0),
            });
            if (code) {
                setAppliedCouponCode(code);
                toast.success('Áp dụng mã giảm giá thành công!');
            } else {
                setAppliedCouponCode('');
            }
        } catch (error) {
            toast.error(getApiError(error, 'Không thể áp dụng mã giảm giá này'));
            if (code) {
                setCouponCodeInput('');
                fetchPreview(cartId, null);
            }
        } finally {
            setIsLoadingPreview(false);
        }
    };

    const handleApplyCoupon = () => {
        if (!couponCodeInput.trim()) {
            toast.warning('Vui lòng nhập mã giảm giá');
            return;
        }
        fetchPreview(dataCart.id, couponCodeInput.trim());
    };

    const handleClearCoupon = () => {
        setCouponCodeInput('');
        fetchPreview(dataCart.id, null);
        toast.info('Đã bỏ chọn mã giảm giá.');
    };

    const validateForm = () => {
        if (!checkBox) {
            toast.error('Vui lòng chấp nhận điều khoản của chúng tôi');
            return false;
        }

        if (!firstName.trim() || !lastName.trim() || !phoneNumber.trim() || !email.trim() || !province.trim() || !addressLine1.trim() || !district.trim() || !ward.trim()) {
            toast.error('Vui lòng điền đầy đủ thông tin');
            return false;
        }

        if (!/@/.test(email)) {
            toast.error('Email không hợp lệ');
            return false;
        }

        if (!/^[0-9]{10}$/.test(phoneNumber)) {
            toast.error('Số điện thoại không hợp lệ');
            return false;
        }

        if (!dataCart?.id || !dataCart?.products?.length) {
            toast.error('Giỏ hàng trống');
            return false;
        }

        return true;
    };

    const saveOrUpdateShippingAddress = async () => {
        const recipientName = `${lastName.trim()} ${firstName.trim()}`.trim();
        const addressData = {
            address_type: 'SHIPPING',
            recipient_name: recipientName,
            phone_number: phoneNumber.trim(),
            address_line1: addressLine1.trim(),
            ward: ward.trim(),
            district: district.trim(),
            city: province.trim(),
            province: province.trim(),
            country_code: 'VN',
            postal_code: '',
            is_default: false,
        };

        if (savedAddressId) {
            // Update existing address to keep profile clean
            const res = await request.patch(`/api/me/addresses/${savedAddressId}`, addressData);
            return res.data;
        } else {
            // Create new address if none exists
            const res = await request.post('/api/me/addresses', addressData);
            return res.data;
        }
    };

    const handlePaymentVnpay = async () => {
        if (!validateForm() || isLoading) return;

        try {
            setIsLoading(true);
            const address = await saveOrUpdateShippingAddress();
            const checkoutRes = await request.post('/api/checkout', {
                cart_id: dataCart.id,
                shipping_address_id: address.id,
                billing_address_id: null,
                coupon_code: appliedCouponCode || null,
                customer_note: `VNPAY - ${email.trim()}`,
            });
            const order = checkoutRes.data;

            // Ask the backend gateway to create a VNPAY payment session and return a redirect URL.
            const gatewayRes = await request.post('/api/payments/gateway', {
                order_id: order.id,
                provider: 'VNPAY',
                return_url: `${window.location.origin}/vnpay/return`,
                idempotency_key: `vnpay-order-${order.id}`,
            });

            const redirectUrl = gatewayRes.data?.redirect_url || gatewayRes.data?.payment_url;
            if (!redirectUrl) {
                throw new Error('Không nhận được liên kết thanh toán VNPAY.');
            }

            dispatch(clearCart());
            window.location.href = redirectUrl;
        } catch (error) {
            if (error?.response?.status === 404) {
                toast.info('Cổng thanh toán VNPAY chưa được kích hoạt. Vui lòng chọn thanh toán khi nhận hàng.');
            } else {
                toast.error(getApiError(error, 'Không thể khởi tạo thanh toán VNPAY'));
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handlePaymentCod = async () => {
        if (!validateForm() || isLoading) return;

        try {
            setIsLoading(true);
            const address = await saveOrUpdateShippingAddress();
            const checkoutRes = await request.post('/api/checkout', {
                cart_id: dataCart.id,
                shipping_address_id: address.id,
                billing_address_id: null,
                coupon_code: appliedCouponCode || null,
                customer_note: `COD - ${email.trim()}`,
            });
            const order = checkoutRes.data;

            const paymentRes = await request.post('/api/payments/cod', {
                order_id: order.id,
                idempotency_key: `cod-order-${order.id}`,
                note: 'Thanh toán khi nhận hàng',
            });
            const payment = paymentRes.data;

            dispatch(clearCart());
            localStorage.setItem('last_cod_checkout', JSON.stringify({ order, payment }));
            toast.success('Đặt hàng COD thành công!');
            navigate('/thanks', { state: { order, payment } });
        } catch (error) {
            toast.error(getApiError(error, 'Không thể đặt hàng COD'));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className={cx('wrapper')}>
            <ToastContainer transition={Bounce} icon={false} />
            <header>
                <Header />
            </header>

            <Loading isLoading={isLoading} />

            <div>
                <Banner />
            </div>

            <main className={cx('inner')}>
                <div className={cx('inner-checkout')}>
                    <div className={cx('column-billing')}>
                        <h1 id={cx('title-billing')}>Thông Tin Thanh Toán</h1>
                        <div className={cx('input-name')}>
                            <div className="input-group mb-3">
                                <input type="text" className="form-control" placeholder="Nhập tên của bạn" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                            </div>

                            <div className="input-group mb-3">
                                <input type="text" className="form-control" placeholder="Nhập họ của bạn" value={lastName} onChange={(e) => setLastName(e.target.value)} />
                            </div>
                        </div>
                        <div className={cx('input-name')}>
                            <div className="input-group mb-3">
                                <input type="text" className="form-control" placeholder="Số điện thoại" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} />
                            </div>

                            <div className="input-group mb-3">
                                <input type="text" className="form-control" placeholder="Email của bạn" value={email} onChange={(e) => setEmail(e.target.value)} />
                            </div>
                        </div>
                        <input type="text" className="form-control" placeholder="Tỉnh/Thành phố" value={province} onChange={(e) => setProvince(e.target.value)} />
                        <div className="mt-5">
                            <div className="input-group mb-3">
                                <input type="text" className="form-control" placeholder="Địa chỉ nhận hàng" value={addressLine1} onChange={(e) => setAddressLine1(e.target.value)} />
                            </div>

                            <div className="input-group mb-3">
                                <input type="text" className="form-control" placeholder="Quận/Huyện" value={district} onChange={(e) => setDistrict(e.target.value)} />
                            </div>

                            <div className="input-group mb-3 mt-3">
                                <input type="text" className="form-control" placeholder="Xã/Phường/Thị trấn" value={ward} onChange={(e) => setWard(e.target.value)} />
                            </div>
                        </div>
                    </div>

                    <div className={cx('form-order')}>
                        <div className={cx('inner-order')}>
                            <h1 id={cx('title-order')}>Sản Phẩm Thanh Toán</h1>

                            <div>
                                <table className="table table-hover">
                                    <thead>
                                        <tr>
                                            <th scope="col">Tên Sản Phẩm</th>
                                            <th scope="col">Số Lượng</th>
                                            <th scope="col">Tổng</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {dataCart?.products?.map((item) => (
                                            <tr key={item?.id}>
                                                <td>{titleOf(item)}</td>
                                                <td>x {item?.quantity}</td>
                                                <td>{formatVndFromDb(item.line_subtotal || item.effective_price)}</td>
                                            </tr>
                                        ))}
                                    </tbody>

                                    <tbody>
                                        <tr>
                                            <td>Tạm Tính</td>
                                            <td></td>
                                            <td>{formatVndFromDb(previewData.subtotal || dataCart?.sumPrice)}</td>
                                        </tr>
                                        {previewData.promotionDiscount > 0 && (
                                            <tr>
                                                <td style={{ color: '#2ecc71', fontWeight: 600 }}>Khuyến Mãi Tự Động</td>
                                                <td></td>
                                                <td style={{ color: '#2ecc71', fontWeight: 600 }}>-{formatVndFromDb(previewData.promotionDiscount)}</td>
                                            </tr>
                                        )}
                                        {previewData.couponDiscount > 0 && (
                                            <tr>
                                                <td style={{ color: '#2ecc71', fontWeight: 600 }}>Mã Giảm Giá ({appliedCouponCode})</td>
                                                <td></td>
                                                <td style={{ color: '#2ecc71', fontWeight: 600 }}>-{formatVndFromDb(previewData.couponDiscount)}</td>
                                            </tr>
                                        )}
                                        {previewData.taxAmount > 0 && (
                                            <tr>
                                                <td style={{ fontWeight: 600 }}>Thuế VAT</td>
                                                <td></td>
                                                <td style={{ fontWeight: 600 }}>+{formatVndFromDb(previewData.taxAmount)}</td>
                                            </tr>
                                        )}
                                        <tr style={{ borderTop: '2px solid #eee', fontWeight: 'bold' }}>
                                            <td>Tổng Cộng</td>
                                            <td></td>
                                            <td>{formatVndFromDb(previewData.total || dataCart?.sumPrice)}</td>
                                        </tr>
                                    </tbody>
                                </table>

                                <div className="input-group mb-3 mt-3">
                                    <input 
                                        type="text" 
                                        className="form-control" 
                                        placeholder="Nhập mã giảm giá (nếu có)" 
                                        value={couponCodeInput} 
                                        onChange={(e) => setCouponCodeInput(e.target.value)} 
                                        disabled={isLoadingPreview}
                                    />
                                    {appliedCouponCode ? (
                                        <button 
                                            className="btn btn-outline-danger" 
                                            type="button" 
                                            onClick={handleClearCoupon}
                                            disabled={isLoadingPreview}
                                        >
                                            {isLoadingPreview ? 'Đang hủy...' : 'Hủy bỏ'}
                                        </button>
                                    ) : (
                                        <button 
                                            className="btn btn-outline-primary" 
                                            type="button" 
                                            onClick={handleApplyCoupon}
                                            disabled={isLoadingPreview}
                                        >
                                            {isLoadingPreview ? 'Đang áp dụng...' : 'Áp dụng'}
                                        </button>
                                    )}
                                </div>

                                {availableCoupons.length > 0 && (
                                    <div className={cx('available-coupons-section')}>
                                        <div 
                                            className={cx('coupons-dropdown-trigger')} 
                                            onClick={() => setShowCouponsDropdown(!showCouponsDropdown)}
                                        >
                                            <span className={cx('trigger-label')}>
                                                {appliedCouponCode 
                                                    ? `Đang áp dụng: ${appliedCouponCode}` 
                                                    : `Bạn có ${availableCoupons.length} mã giảm giá áp dụng được`}
                                            </span>
                                            {appliedCouponCode && (
                                                <button 
                                                    className={cx('clear-coupon-btn')} 
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleClearCoupon();
                                                    }}
                                                    type="button"
                                                >
                                                    ✕ Bỏ chọn
                                                </button>
                                            )}
                                            <span className={cx('dropdown-arrow', { open: showCouponsDropdown })}>▾</span>
                                        </div>
                                        {showCouponsDropdown && (
                                            <div className={cx('coupons-list-wrapper')}>
                                                {availableCoupons.map((coupon) => (
                                                    <div 
                                                        key={coupon.id} 
                                                        className={cx('coupon-badge-card', { active: appliedCouponCode === coupon.code })}
                                                        onClick={() => {
                                                            if (isLoadingPreview) return;
                                                            setCouponCodeInput(coupon.code);
                                                            fetchPreview(dataCart.id, coupon.code);
                                                            setShowCouponsDropdown(false);
                                                        }}
                                                    >
                                                        <div className={cx('coupon-badge-left')}>
                                                            <span className={cx('coupon-code-text')}>{coupon.code}</span>
                                                        </div>
                                                        <div className={cx('coupon-badge-right')}>
                                                            <span className={cx('coupon-name-text')}>{coupon.name}</span>
                                                            <span className={cx('coupon-desc-text')}>
                                                                {coupon.discount_type === 'PERCENTAGE' 
                                                                    ? `Giảm ${coupon.discount_value}%` 
                                                                    : `Giảm ${formatVndFromDb(coupon.discount_value)}`}
                                                                {coupon.min_order_amount > 0 && ` (Đơn tối thiểu ${formatVndFromDb(coupon.min_order_amount)})`}
                                                            </span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                            <div className={cx('form-pay')}>
                                <div className={cx('payment-methods')}>
                                    <span className={cx('payment-methods-title')}>Phương thức thanh toán</span>

                                    <label className={cx('payment-option', paymentMethod === 'COD' && 'payment-option-active')}>
                                        <input
                                            type="radio"
                                            name="paymentMethod"
                                            value="COD"
                                            checked={paymentMethod === 'COD'}
                                            onChange={() => setPaymentMethod('COD')}
                                        />
                                        <span className={cx('payment-option-body')}>
                                            <span className={cx('payment-option-name')}>Thanh toán khi nhận hàng (COD)</span>
                                            <span className={cx('payment-option-desc')}>Trả tiền mặt cho nhân viên giao hàng khi nhận sản phẩm.</span>
                                        </span>
                                    </label>

                                    <label className={cx('payment-option', paymentMethod === 'VNPAY' && 'payment-option-active')}>
                                        <input
                                            type="radio"
                                            name="paymentMethod"
                                            value="VNPAY"
                                            checked={paymentMethod === 'VNPAY'}
                                            onChange={() => setPaymentMethod('VNPAY')}
                                        />
                                        <span className={cx('payment-option-body')}>
                                            <span className={cx('payment-option-name')}>
                                                <img
                                                    src="https://cdn.haitrieu.com/wp-content/uploads/2022/10/Icon-VNPAY-QR.png"
                                                    alt="VNPAY"
                                                    className={cx('payment-option-logo')}
                                                />
                                                Thanh toán qua VNPAY
                                            </span>
                                            <span className={cx('payment-option-desc')}>Thanh toán trực tuyến qua cổng VNPAY (thẻ ATM, QR, ví điện tử).</span>
                                        </span>
                                    </label>
                                </div>

                                <div className={cx('checkbox-terms')}>
                                    <input checked={checkBox} onChange={(e) => setCheckBox(e.target.checked)} type="checkbox" />
                                    <label>Vui lòng chấp nhận điều khoản của chúng tôi</label>
                                </div>

                                <div className={cx('continue')}>
                                    <button
                                        type="button"
                                        onClick={paymentMethod === 'VNPAY' ? handlePaymentVnpay : handlePaymentCod}
                                        disabled={isLoading}
                                    >
                                        <span>
                                            {isLoading
                                                ? 'Đang xử lý...'
                                                : paymentMethod === 'VNPAY'
                                                  ? 'Thanh Toán Qua VNPAY'
                                                  : 'Thanh Toán Khi Nhận Hàng'}
                                        </span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            <footer>
                <Footer />
            </footer>
        </div>
    );
}

export default Checkout;
