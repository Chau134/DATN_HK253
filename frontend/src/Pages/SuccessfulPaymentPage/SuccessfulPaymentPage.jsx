import { useMemo } from 'react';
import classNames from 'classnames/bind';
import { Link, useLocation } from 'react-router-dom';

import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import imgCheck from './img/imgCheck.png';
import { formatVndFromDb } from '../../utils/price';
import styles from './SuccessfulPaymentPage.module.scss';
import { titleOf } from '../../utils/productDisplay';

const cx = classNames.bind(styles);

function readStoredCheckout() {
    try {
        return JSON.parse(localStorage.getItem('last_cod_checkout') || '{}');
    } catch {
        return {};
    }
}

function SuccessfulPaymentPage() {
    const location = useLocation();
    const checkoutData = useMemo(() => location.state || readStoredCheckout(), [location.state]);
    const orderData = checkoutData?.order || null;
    const paymentData = checkoutData?.payment || null;

    const items = orderData?.items || [];
    const createdAt = orderData?.created_at || orderData?.placed_at || orderData?.updated_at;

    return (
        <div className={cx('wrapper')}>
            <header>
                <Header />
            </header>

            <main className={cx('inner')}>
                <div className={cx('form-thanks-order')}>
                    <header className={cx('header')}>
                        <img src={imgCheck} alt="Đặt hàng thành công" />

                        {!orderData ? (
                            <div className={cx('error-message')}>
                                <h3>Chưa có thông tin đơn hàng</h3>
                                <p>Vui lòng kiểm tra lại lịch sử đơn hàng của bạn.</p>
                                <Link to="/order-history" className={cx('back-home')}>
                                    Xem lịch sử đơn hàng
                                </Link>
                            </div>
                        ) : (
                            <>
                                <h3>Cảm ơn bạn đã đặt hàng!</h3>
                                <p>Đơn hàng COD của bạn đã được tiếp nhận. Cửa hàng sẽ liên hệ và xử lý trong thời gian sớm nhất.</p>
                            </>
                        )}
                    </header>

                    {orderData && (
                        <main>
                            <div>
                                <div className={cx('order-info')}>
                                    <p>
                                        Mã đơn hàng: <strong>{orderData.order_number || orderData.id}</strong>
                                    </p>
                                    {createdAt && (
                                        <p>
                                            Ngày đặt hàng: <strong>{new Date(createdAt).toLocaleString('vi-VN')}</strong>
                                        </p>
                                    )}
                                    <p>
                                        Mã thanh toán: <strong>{paymentData?.payment_number || paymentData?.id || 'COD'}</strong>
                                    </p>
                                </div>

                                <table className={cx('table table-hover')}>
                                    <thead>
                                        <tr>
                                            <th scope="col">Sản phẩm</th>
                                            <th scope="col">Số lượng</th>
                                            <th scope="col">Đơn giá</th>
                                            <th scope="col">Thành tiền</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {items.map((item) => (
                                            <tr key={item.id}>
                                                <td>{titleOf(item)}</td>
                                                <td>{item.quantity}</td>
                                                <td>{formatVndFromDb(item.effective_unit_price || item.unit_price)}</td>
                                                <td>{formatVndFromDb(item.line_total || item.line_subtotal)}</td>
                                            </tr>
                                        ))}
                                    </tbody>

                                    <tfoot>
                                        <tr className={cx('total-row')}>
                                            <td colSpan="3">Tổng cộng</td>
                                            <td className={cx('total-price')}>{formatVndFromDb(orderData.total_amount)}</td>
                                        </tr>
                                        <tr>
                                            <td colSpan="4" className={cx('payment-status')}>
                                                Trạng thái thanh toán: <span className={cx('unpaid')}>Thanh toán khi nhận hàng</span>
                                            </td>
                                        </tr>
                                    </tfoot>
                                </table>

                                <div className={cx('actions')}>
                                    <Link to="/" className={cx('continue-shopping')}>
                                        Tiếp tục mua sắm
                                    </Link>
                                    <Link to="/order-history" className={cx('view-orders')}>
                                        Xem lịch sử đơn hàng
                                    </Link>
                                </div>
                            </div>
                        </main>
                    )}
                </div>
            </main>

            <footer>
                <Footer />
            </footer>
        </div>
    );
}

export default SuccessfulPaymentPage;
