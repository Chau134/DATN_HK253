import { useEffect, useState } from 'react';

import { ModalEditOrder } from '../../../Modal/Modal';
import classNames from 'classnames/bind';
import styles from './OderProducts.module.scss';
import { fetchAdminOrders } from '../../../../../api/adminCatalogApi';

const cx = classNames.bind(styles);

const statusLabel = (status) => {
    const labels = {
        PENDING: 'Chờ xử lý',
        CONFIRMED: 'Đã tiếp nhận',
        PAID: 'Đã xác nhận COD',
        PACKING: 'Đang đóng gói',
        SHIPPING: 'Đang vận chuyển',
        DELIVERED: 'Đã giao, chờ khách xác nhận',
        COMPLETED: 'Hoàn thành',
        CANCELLED: 'Đã hủy',
        REFUNDED: 'Đã hoàn tiền',
    };
    return labels[status] || status || 'Chưa rõ';
};

function OrderProducts() {
    const [dataOrder, setDataOrder] = useState([]);
    const [show, setShow] = useState(false);
    const [id, setId] = useState('');
    const [selectedOrder, setSelectedOrder] = useState(null);

    const loadOrders = () => {
        fetchAdminOrders().then(setDataOrder).catch(() => setDataOrder([]));
    };

    useEffect(() => {
        loadOrders();
    }, []);

    const handleShowModal = (order) => {
        setShow(true);
        setId(order._id);
        setSelectedOrder(order);
    };

    return (
        <div className={cx('wrapper')}>
            <h1>Đơn hàng</h1>
            {dataOrder.map((item) => (
                <table key={item._id} className={cx('order-table', 'table')}>
                    <thead>
                        <tr>
                            <th scope="col">Email người dùng</th>
                            <th scope="col">Tên sản phẩm</th>
                            <th scope="col">Trạng thái</th>
                            <th scope="col">Thanh toán</th>
                            <th scope="col">Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{item.email}</td>
                            <td>
                                <div className={cx('products-list')}>
                                    {item?.products.map((product, index) => (
                                        <span key={`${item._id}-${index}`}>{product.nameProduct}</span>
                                    ))}
                                </div>
                            </td>
                            <td>{statusLabel(item.status)}</td>
                            <td>
                                {item.statusPayment ? 'Đã thanh toán' : 'Chưa thanh toán'}
                                {item.canConfirmCod ? ' - Chờ admin xác nhận COD' : ''}
                            </td>
                            <td>
                                <button
                                    onClick={() => handleShowModal(item)}
                                    type="button"
                                    className={cx('edit-button')}
                                >
                                    Chỉnh sửa
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            ))}
            <ModalEditOrder show={show} setShow={setShow} id={id} order={selectedOrder} onSaved={loadOrders} />
        </div>
    );
}

export default OrderProducts;
