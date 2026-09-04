import { useEffect, useMemo, useState } from 'react';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import { toast, ToastContainer } from 'react-toastify';
import classNames from 'classnames/bind';

import request, { getApiError } from '../../../config/Connect';
import styles from './Modal.module.scss';

const cx = classNames.bind(styles);

const STATUS_OPTIONS = {
    PENDING: [{ value: 'CONFIRMED', label: 'Xác nhận đơn' }, { value: 'CANCELLED', label: 'Hủy đơn' }],
    CONFIRMED: [{ value: 'CANCELLED', label: 'Hủy đơn' }],
    PAID: [{ value: 'PACKING', label: 'Đóng gói' }],
    PACKING: [{ value: 'SHIPPING', label: 'Đang vận chuyển' }],
    SHIPPING: [{ value: 'DELIVERED', label: 'Đã giao hàng' }],
};

export function CheckProduct({ show, setShow, idProduct }) {
    const handleClose = () => setShow(false);

    const handleCheckProduct = async () => {
        toast.error('Hãy cập nhật trạng thái đơn hàng bằng modal chỉnh sửa đơn hàng.');
    };

    return (
        <div>
            <Modal show={show} onHide={handleClose}>
                <ToastContainer />
                <Modal.Header closeButton>
                    <Modal.Title>Duyệt đơn hàng</Modal.Title>
                </Modal.Header>
                <Modal.Body>Duyệt đơn hàng cho: {idProduct}</Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleClose}>
                        Đóng
                    </Button>
                    <Button variant="primary" onClick={handleCheckProduct}>
                        Duyệt
                    </Button>
                </Modal.Footer>
            </Modal>
        </div>
    );
}

export function ModalEditOrder({ show, setShow, id, order, onSaved }) {
    const handleClose = () => setShow(false);
    const [nextStatus, setNextStatus] = useState('');
    const [note, setNote] = useState('');
    const statusOptions = useMemo(() => STATUS_OPTIONS[order?.status] || [], [order?.status]);

    useEffect(() => {
        if (!show) return;
        setNextStatus(statusOptions[0]?.value || '');
        setNote('');
    }, [show, statusOptions]);

    const refreshAndClose = () => {
        onSaved?.();
        handleClose();
    };

    const handleConfirmCod = async () => {
        if (!order?.paymentId) {
            toast.error('Không tìm thấy payment COD của đơn hàng.');
            return;
        }

        try {
            await request.post(`/admin/payments/${order.paymentId}/cod/confirm`, {
                reason: 'admin_confirm_cod_order',
                note: note || 'Admin xác nhận đơn COD và trừ kho',
            });
            toast.success('Đã xác nhận COD và trừ tồn kho.');
            refreshAndClose();
        } catch (error) {
            toast.error(getApiError(error, 'Xác nhận COD thất bại'));
        }
    };

    const handleEditOrder = async () => {
        if (!nextStatus) {
            toast.error('Không có trạng thái hợp lệ để cập nhật.');
            return;
        }

        try {
            await request.patch(`/admin/orders/${id}/status`, {
                status: nextStatus,
                reason: 'admin_order_status_update',
                note: note || 'Cập nhật từ admin',
            });
            toast.success('Cập nhật đơn hàng thành công.');
            refreshAndClose();
        } catch (error) {
            toast.error(getApiError(error, 'Cập nhật đơn hàng thất bại'));
        }
    };

    return (
        <>
            <Modal show={show} onHide={handleClose} size="lg" contentClassName="admin-edit-modal">
                <Modal.Header closeButton>
                    <Modal.Title>Chỉnh sửa đơn hàng</Modal.Title>
                </Modal.Header>
                <Modal.Body className={cx('product-edit-body')}>
                    <div className={cx('product-edit-box-title')}>
                        <h4>Chỉnh sửa đơn hàng</h4>
                    </div>

                    <section className={cx('product-edit-section')}>
                        <h5>Thông tin trạng thái</h5>
                        <div className={cx('product-edit-grid')}>
                            <label>
                                Trạng thái hiện tại
                                <input className="form-control" value={order?.status || ''} disabled />
                            </label>

                            <label>
                                Cập nhật trạng thái vận hành
                                <select
                                    value={nextStatus}
                                    onChange={(e) => setNextStatus(e.target.value)}
                                    className="form-select"
                                    disabled={statusOptions.length === 0}
                                >
                                    {statusOptions.length === 0 ? (
                                        <option>Không có bước tiếp theo</option>
                                    ) : (
                                        statusOptions.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))
                                    )}
                                </select>
                            </label>
                        </div>
                    </section>

                    {order?.canConfirmCod && (
                        <div className="alert alert-warning mb-0">
                            Đơn COD đang chờ admin xác nhận. Bấm xác nhận COD để chuyển đơn sang đang giao hàng và trừ
                            tồn kho.
                        </div>
                    )}

                    <section className={cx('product-edit-section')}>
                        <h5>Thông tin bổ sung</h5>
                        <div>
                            <label>
                                Ghi chú
                                <textarea
                                    value={note}
                                    onChange={(e) => setNote(e.target.value)}
                                    className="form-control"
                                    rows="3"
                                    placeholder="Ghi chú xử lý đơn hàng"
                                />
                            </label>
                        </div>
                    </section>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleClose}>
                        Đóng
                    </Button>
                    {order?.canConfirmCod && (
                        <Button variant="success" onClick={handleConfirmCod}>
                            Xác nhận COD & trừ kho
                        </Button>
                    )}
                    <Button variant="primary" onClick={handleEditOrder} disabled={!nextStatus}>
                        Lưu trạng thái
                    </Button>
                </Modal.Footer>
            </Modal>
        </>
    );
}
