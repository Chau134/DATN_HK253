import React, { useEffect, useMemo, useState } from 'react';
import classNames from 'classnames/bind';
import { Link, useLocation } from 'react-router-dom';
import { CheckCircle, XCircle, Loader } from 'lucide-react';

import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import styles from './VnpayReturn.module.scss';

const cx = classNames.bind(styles);

// VNPAY returns "00" in vnp_ResponseCode / vnp_TransactionStatus on success.
function isSuccessCode(params) {
    const responseCode = params.get('vnp_ResponseCode');
    const transactionStatus = params.get('vnp_TransactionStatus');
    if (responseCode || transactionStatus) {
        return responseCode === '00' && (transactionStatus === '00' || transactionStatus === null);
    }
    // Fallback for a generic gateway that returns ?status=success
    const status = (params.get('status') || '').toLowerCase();
    return status === 'success' || status === 'paid';
}

function VnpayReturn() {
    const location = useLocation();
    const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const [state, setState] = useState('pending');

    const orderRef = params.get('vnp_TxnRef') || params.get('order_id') || '';
    const amount = params.get('vnp_Amount');

    useEffect(() => {
        // No query params means the user opened the page directly.
        if (![...params.keys()].length) {
            setState('unknown');
            return;
        }
        setState(isSuccessCode(params) ? 'success' : 'failed');
    }, [params]);

    return (
        <div className={cx('wrapper')}>
            <header><Header /></header>
            <main className={cx('inner')}>
                <div className={cx('card')}>
                    {state === 'pending' && (
                        <>
                            <Loader className={cx('icon', 'spin')} size={64} />
                            <h1>Đang xác nhận thanh toán...</h1>
                        </>
                    )}

                    {state === 'success' && (
                        <>
                            <CheckCircle className={cx('icon', 'success')} size={64} />
                            <h1>Thanh toán thành công</h1>
                            <p>Cảm ơn bạn đã mua sắm. Đơn hàng của bạn đang được xử lý.</p>
                            {orderRef && <p className={cx('meta')}>Mã tham chiếu: {orderRef}</p>}
                            {amount && <p className={cx('meta')}>Số tiền: {(Number(amount) / 100).toLocaleString('vi-VN')}đ</p>}
                            <div className={cx('actions')}>
                                <Link to="/order-history" className={cx('primary')}>Xem đơn hàng</Link>
                                <Link to="/category" className={cx('secondary')}>Tiếp tục mua sắm</Link>
                            </div>
                        </>
                    )}

                    {state === 'failed' && (
                        <>
                            <XCircle className={cx('icon', 'failed')} size={64} />
                            <h1>Thanh toán không thành công</h1>
                            <p>Giao dịch đã bị hủy hoặc gặp lỗi. Bạn có thể thử lại hoặc chọn thanh toán khi nhận hàng.</p>
                            <div className={cx('actions')}>
                                <Link to="/cart" className={cx('primary')}>Quay lại giỏ hàng</Link>
                                <Link to="/category" className={cx('secondary')}>Tiếp tục mua sắm</Link>
                            </div>
                        </>
                    )}

                    {state === 'unknown' && (
                        <>
                            <XCircle className={cx('icon', 'failed')} size={64} />
                            <h1>Không có thông tin thanh toán</h1>
                            <p>Trang này hiển thị kết quả sau khi bạn thanh toán qua VNPAY.</p>
                            <div className={cx('actions')}>
                                <Link to="/category" className={cx('primary')}>Về trang sản phẩm</Link>
                            </div>
                        </>
                    )}
                </div>
            </main>
            <footer><Footer /></footer>
        </div>
    );
}

export default VnpayReturn;
