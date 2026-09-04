import { useEffect, useState } from 'react';
import classNames from 'classnames/bind';
import styles from './OrderHistory.module.scss';

import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import request from '../../config/Connect';
import { Link, useNavigate } from 'react-router-dom';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import Loading from '../../Layouts/Loading/Loading';
import ModalFeedBack from '../InfoUser/modal/ModalFeedBack';
import { formatVndFromDb } from '../../utils/price';
import OrderTimeline from '../../components/OrderTimeline/OrderTimeline';
import { titleOf } from '../../utils/productDisplay';

const cx = classNames.bind(styles);

const normalizeItem = (item) => ({
    id: item?.id,
    productId: item?.source_product_id || item?.product_id || item?.productId,
    orderItemId: item?.id,
    nameProduct: titleOf(item),
    quantity: Number(item?.quantity || 0),
    price: Number(item?.effective_unit_price ?? item?.unit_price ?? 0),
    isReviewed: item?.is_reviewed || item?.isReviewed || false,
});

const normalizeOrder = (order) => {
    const status = order?.status || 'PENDING';
    const products = Array.isArray(order?.items)
        ? order.items.map(normalizeItem)
        : order?.products || [
              {
                  nameProduct: order?.order_number || `Đơn hàng ${order?.id}`,
                  quantity: order?.item_count || 0,
                  price: Number(order?.total_amount || 0),
              },
          ];

    const isReviewed = order?.is_reviewed || order?.isReviewed || (Array.isArray(order?.items) && order.items.length > 0 && products.every(p => p.isReviewed));

    return {
        ...order,
        _id: order?.id,
        idCode: order?.order_number,
        status,
        products,
        sumPrice: Number(order?.total_amount || order?.sumPrice || 0),
        createdAt: order?.placed_at || order?.created_at || order?.createdAt,
        statusPayment: order?.latest_payment?.status === 'PAID',
        order: ['CANCELLED', 'REFUNDED'].includes(status),
        statusOrder: ['DELIVERED', 'COMPLETED'].includes(status),
        canCancel: ['PENDING', 'CONFIRMED'].includes(status),
        canConfirmReceived: status === 'SHIPPING' || status === 'DELIVERED',
        canReview: status === 'COMPLETED',
        isReviewed,
    };
};

const statusLabel = (status) => {
    const labels = {
        PENDING: 'Chờ xử lý',
        CONFIRMED: 'Đã tiếp nhận',
        PAID: 'Đã xác nhận',
        PACKING: 'Đang đóng gói',
        SHIPPING: 'Đang vận chuyển',
        DELIVERED: 'Đã giao, chờ xác nhận',
        COMPLETED: 'Hoàn thành',
        CANCELLED: 'Đã hủy',
        REFUNDED: 'Đã hoàn tiền',
    };
    return labels[status] || status || 'Đang xử lý';
};

const statusClass = (status) => {
    if (['CANCELLED', 'REFUNDED'].includes(status)) return 'cancelled';
    if (status === 'COMPLETED') return 'completed';
    return 'processing';
};

function OrderHistory() {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('all');
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [feedbackData, setFeedbackData] = useState(null);
    const [dataUser, setDataUser] = useState(null);
    const navigate = useNavigate();

    const fetchOrders = async () => {
        try {
            setLoading(true);
            const response = await request.get('/api/orders');
            if (Array.isArray(response.data)) {
                const sortedOrders = response.data
                    .map(normalizeOrder)
                    .sort((a, b) => new Date(b.createdAt || Date.now()) - new Date(a.createdAt || Date.now()));
                setOrders(sortedOrders);
                setError(null);
            } else {
                setError('Không thể tải dữ liệu đơn hàng');
            }
        } catch (fetchError) {
            console.error('Lỗi khi tải lịch sử đơn hàng:', fetchError);
            setError('Đã xảy ra lỗi khi tải dữ liệu đơn hàng');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        request.get('/api/me').then((res) => setDataUser(res.data)).catch(() => null);
    }, []);

    useEffect(() => {
        fetchOrders();
    }, [navigate]);

    const handleShowDetails = async (order) => {
        if (selectedOrder?._id === order._id) {
            setSelectedOrder(null);
            return;
        }

        if (order.items || order.products?.[0]?.orderItemId) {
            setSelectedOrder(order);
            return;
        }

        try {
            const response = await request.get(`/api/orders/${order._id}`);
            const detailedOrder = normalizeOrder(response.data);
            setOrders((prev) => prev.map((item) => (item._id === detailedOrder._id ? detailedOrder : item)));
            setSelectedOrder(detailedOrder);
        } catch {
            toast.error('Không thể tải chi tiết đơn hàng.');
        }
    };

    const handleReviewedSuccess = (orderId) => {
        setOrders((prev) => prev.map((order) => (order._id === orderId ? { ...order, isReviewed: true } : order)));
    };

    const openFeedbackModal = async (order) => {
        if (order.products?.[0]?.orderItemId) {
            setFeedbackData(order);
            setShowModal(true);
            return;
        }

        try {
            const response = await request.get(`/api/orders/${order._id}`);
            const detailedOrder = normalizeOrder(response.data);
            setOrders((prev) => prev.map((item) => (item._id === detailedOrder._id ? detailedOrder : item)));
            setFeedbackData(detailedOrder);
            setShowModal(true);
        } catch {
            toast.error('Không thể tải sản phẩm để đánh giá.');
        }
    };

    const handleDeleteOrder = async (id) => {
        if (!window.confirm('Bạn có chắc chắn muốn hủy đơn hàng này không?')) {
            return;
        }

        try {
            setLoading(true);
            await request.post(`/api/orders/${id}/cancel`, { reason: 'cancelled_from_client' });
            toast.success('Đã hủy đơn hàng thành công');
            await fetchOrders();
        } catch (cancelError) {
            console.error('Lỗi khi hủy đơn hàng:', cancelError);
            toast.error('Không thể hủy đơn hàng. Vui lòng thử lại sau.');
        } finally {
            setLoading(false);
        }
    };

    const handleConfirmReceived = async (order) => {
        if (!window.confirm('Xác nhận bạn đã nhận được đơn hàng này?')) {
            return;
        }

        try {
            setLoading(true);
            const response = await request.post(`/api/orders/${order._id}/received`);
            const completedOrder = normalizeOrder(response.data);
            setOrders((prev) => prev.map((item) => (item._id === completedOrder._id ? completedOrder : item)));
            setSelectedOrder((prev) => (prev?._id === completedOrder._id ? completedOrder : prev));
            toast.success('Cảm ơn bạn đã xác nhận nhận hàng.');
        } catch {
            toast.error('Không thể xác nhận nhận hàng. Vui lòng thử lại sau.');
        } finally {
            setLoading(false);
        }
    };

    const getFilteredOrders = () => {
        switch (activeTab) {
            case 'processing':
                return orders.filter((order) => !['COMPLETED', 'CANCELLED', 'REFUNDED'].includes(order.status));
            case 'completed':
                return orders.filter((order) => order.status === 'COMPLETED');
            case 'cancelled':
                return orders.filter((order) => ['CANCELLED', 'REFUNDED'].includes(order.status));
            default:
                return orders;
        }
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('vi-VN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const calculateItemTotal = (price, quantity) => price * quantity;

    return (
        <div className={cx('wrapper')}>
            <ToastContainer />
            <Loading isLoading={loading} />

            <header>
                <Header />
            </header>

            <main className={cx('container')}>
                <div className={cx('page-header')}>
                    <h1>Lịch sử đơn hàng</h1>
                    <p>Xem và quản lý các đơn hàng của bạn</p>
                </div>

                {error ? (
                    <div className={cx('error-message')}>
                        <p>{error}</p>
                        <Link to="/" className={cx('back-home')}>
                            Quay về trang chủ
                        </Link>
                    </div>
                ) : (
                    <>
                        <div className={cx('tabs')}>
                            <button className={cx('tab', { active: activeTab === 'all' })} onClick={() => setActiveTab('all')}>
                                Tất cả
                            </button>
                            <button
                                className={cx('tab', { active: activeTab === 'processing' })}
                                onClick={() => setActiveTab('processing')}
                            >
                                Đang xử lý
                            </button>
                            <button
                                className={cx('tab', { active: activeTab === 'completed' })}
                                onClick={() => setActiveTab('completed')}
                            >
                                Hoàn thành
                            </button>
                            <button
                                className={cx('tab', { active: activeTab === 'cancelled' })}
                                onClick={() => setActiveTab('cancelled')}
                            >
                                Đã hủy
                            </button>
                        </div>

                        {getFilteredOrders().length === 0 ? (
                            <div className={cx('no-orders')}>
                                <p>Không có đơn hàng nào trong mục này</p>
                                <Link to="/" className={cx('shop-now')}>
                                    Mua sắm ngay
                                </Link>
                            </div>
                        ) : (
                            <div className={cx('orders-list')}>
                                {getFilteredOrders().map((order) => (
                                    <div key={order._id} className={cx('order-card')}>
                                        <div className={cx('order-header')}>
                                            <div className={cx('order-info')}>
                                                <span className={cx('order-id')}>Mã đơn: {order.idCode || order._id}</span>
                                                <span className={cx('order-date')}>Ngày đặt: {formatDate(order.createdAt)}</span>
                                            </div>
                                            <div className={cx('order-status')}>
                                                <span className={cx('status', statusClass(order.status))}>{statusLabel(order.status)}</span>
                                            </div>
                                        </div>

                                        <div className={cx('order-products')}>
                                            {order.products.slice(0, 2).map((product, index) => (
                                                <div key={`${order._id}-${index}`} className={cx('product-item')}>
                                                    <div className={cx('product-name')}>{product.nameProduct}</div>
                                                    <div className={cx('product-details')}>
                                                        <span className={cx('product-quantity')}>x{product.quantity}</span>
                                                        <span className={cx('product-price')}>{formatVndFromDb(product.price)}</span>
                                                    </div>
                                                </div>
                                            ))}
                                            {order.products.length > 2 && (
                                                <div className={cx('more-products')}>+{order.products.length - 2} sản phẩm khác</div>
                                            )}
                                        </div>

                                        <div className={cx('order-footer')}>
                                            <div className={cx('order-total')}>
                                                <span>Tổng tiền:</span>
                                                <span className={cx('total-price')}>{formatVndFromDb(order.sumPrice)}</span>
                                            </div>

                                            <div className={cx('payment-status')}>
                                                {order.statusPayment ? (
                                                    <span className={cx('paid')}>Đã thanh toán</span>
                                                ) : (
                                                    <span className={cx('unpaid')}>Thanh toán khi nhận hàng</span>
                                                )}
                                            </div>

                                            <div className={cx('order-actions')}>
                                                {order.canCancel && (
                                                    <button onClick={() => handleDeleteOrder(order._id)} className={cx('cancel-button')}>
                                                        Hủy đơn hàng
                                                    </button>
                                                )}

                                                {order.canConfirmReceived && (
                                                    <button
                                                        onClick={() => handleConfirmReceived(order)}
                                                        className={cx('confirm-received-button')}
                                                    >
                                                        Đã nhận hàng
                                                    </button>
                                                )}

                                                {order.canReview && !order.isReviewed && (
                                                    <button onClick={() => openFeedbackModal(order)} className={cx('review-button')}>
                                                        Đánh giá
                                                    </button>
                                                )}

                                                {order.canReview && order.isReviewed && (
                                                    <button className={cx('reviewed-button')} disabled>
                                                        Đã đánh giá
                                                    </button>
                                                )}

                                                <button className={cx('details-button')} onClick={() => handleShowDetails(order)}>
                                                    {selectedOrder?._id === order._id ? 'Ẩn chi tiết' : 'Chi tiết'}
                                                </button>
                                            </div>
                                        </div>

                                        {selectedOrder?._id === order._id && (
                                            <div className={cx('order-detail')}>
                                                <div className={cx('order-detail-header')}>
                                                    <div>
                                                        <strong>Mã đơn hàng:</strong> {selectedOrder.idCode || selectedOrder._id}
                                                    </div>
                                                    <div>
                                                        <strong>Ngày đặt:</strong> {formatDate(selectedOrder.createdAt)}
                                                    </div>
                                                    <div>
                                                        <strong>Trạng thái:</strong>{' '}
                                                        <span className={cx('status', statusClass(selectedOrder.status))}>
                                                            {statusLabel(selectedOrder.status)}
                                                        </span>
                                                    </div>
                                                    <div>
                                                        <strong>Thanh toán:</strong>{' '}
                                                        {selectedOrder.statusPayment ? (
                                                            <span className={cx('paid')}>Đã thanh toán</span>
                                                        ) : (
                                                            <span className={cx('unpaid')}>Thanh toán khi nhận hàng</span>
                                                        )}
                                                    </div>
                                                </div>

                                                <OrderTimeline status={selectedOrder.status} />

                                                <h5>Sản phẩm</h5>
                                                <table className={cx('product-table')}>
                                                    <thead>
                                                        <tr>
                                                            <th>Sản phẩm</th>
                                                            <th>Số lượng</th>
                                                            <th>Đơn giá</th>
                                                            <th>Thành tiền</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {selectedOrder.products.map((product, index) => (
                                                            <tr key={`${selectedOrder._id}-detail-${index}`}>
                                                                <td>{product.nameProduct}</td>
                                                                <td>{product.quantity}</td>
                                                                <td>{formatVndFromDb(product.price)}</td>
                                                                <td>{formatVndFromDb(calculateItemTotal(product.price, product.quantity))}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                    <tfoot>
                                                        <tr>
                                                            <td colSpan="3" className={cx('total-label')}>
                                                                Tổng cộng
                                                            </td>
                                                            <td className={cx('total-value')}>{formatVndFromDb(selectedOrder.sumPrice)}</td>
                                                        </tr>
                                                    </tfoot>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </main>

            <footer>
                <Footer />
            </footer>
            <ModalFeedBack
                showModalFeedBack={showModal}
                setShowModalFeedBack={setShowModal}
                data={feedbackData}
                dataUser={dataUser}
                onReviewedSuccess={handleReviewedSuccess}
            />
        </div>
    );
}

export default OrderHistory;
