import React, { useState, useEffect } from 'react';
import Modal from 'react-bootstrap/Modal';
import { toast } from 'react-toastify';
import request from '../../../config/Connect';


function ModalFeedBack({ showModalFeedBack, setShowModalFeedBack, data, dataUser, onReviewedSuccess }) {
    const handleClose = () => setShowModalFeedBack(false);

    const [feedbacks, setFeedbacks] = useState([]);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async () => {
        if (submitting) return;

        // validate
        for (const f of feedbacks) {
            if (!f.isReviewed && (f.rating < 1 || f.rating > 5)) {
                toast.error('Vui lòng chọn số sao cho tất cả sản phẩm');
                return;
            }
        }

        try {
            setSubmitting(true);

            const toSubmit = feedbacks.filter(f => !f.isReviewed);
            if (toSubmit.length > 0) {
                await Promise.all(toSubmit.map((feedback) => {
                    if (!feedback.orderItemId) {
                        throw new Error('Thieu order_item_id de gui danh gia qua Spring Boot.');
                    }

                    return request.post('/api/reviews', {
                        order_item_id: feedback.orderItemId,
                        rating: feedback.rating,
                        content: feedback.comment,
                    });
                }));
            }

            toast.success('Đánh giá thành công!');
            if (onReviewedSuccess) {
                onReviewedSuccess(data._id);
            }

            handleClose();
        } catch (err) {
            toast.error(err.response?.data?.message || 'Gửi đánh giá thất bại!');
        } finally {
            setSubmitting(false);
        }
    };

    useEffect(() => {
        const products = data?.products || data?.items || [];
        setFeedbacks(products.map(p => ({
            productId: p.product_id || p.productId,
            orderItemId: p.order_item_id || p.orderItemId || p.id,
            rating: p.isReviewed ? 5 : 0,
            comment: p.isReviewed ? 'Đã đánh giá' : '',
            isReviewed: p.isReviewed || false,
        })));
    }, [data]);

    const handleChange = (productId, field, value) => {
        setFeedbacks(prev =>
            prev.map(f => (f.productId === productId ? { ...f, [field]: value } : f))
        );
    };

    return (
        <Modal show={showModalFeedBack} onHide={handleClose}>
            <Modal.Header closeButton>
                <Modal.Title>Đánh Giá Sản Phẩm</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <table className="table table-bordered border-primary">
                    <thead>
                        <tr>
                            <th>Sản Phẩm</th>
                            <th>Số Sao</th>
                            <th>Bình Luận</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data?.products?.length > 0 ? (
                            data.products.map((p, index) => (
                            <tr key={p.productId}>
                                <td>{p.nameProduct}</td>
                                <td>
                                <select
                                    value={feedbacks[index]?.rating || 0}
                                    onChange={(e) =>
                                    handleChange(p.productId, 'rating', Number(e.target.value))
                                    }
                                    disabled={p.isReviewed}
                                >
                                    <option value={0}>Chọn sao</option>
                                    {[1,2,3,4,5].map(n => <option key={n} value={n}>{n} ⭐</option>)}
                                </select>
                                </td>
                                <td>
                                <input
                                    type="text"
                                    value={feedbacks[index]?.comment || ''}
                                    onChange={(e) =>
                                    handleChange(p.productId, 'comment', e.target.value)
                                    }
                                    placeholder={p.isReviewed ? "Đã đánh giá" : "Nhập bình luận"}
                                    className="form-control"
                                    disabled={p.isReviewed}
                                />
                                </td>
                            </tr>
                            ))
                        ) : (
                            <tr>
                            <td colSpan={3}>Không có sản phẩm để đánh giá</td>
                            </tr>
                        )}
                        </tbody>

                </table>
                 <button
                className="btn btn-success mt-3"
                onClick={handleSubmit}
                disabled={submitting || (feedbacks.length > 0 && feedbacks.every(f => f.isReviewed))}
            >
                {submitting ? 'Đang gửi...' : (feedbacks.length > 0 && feedbacks.every(f => f.isReviewed)) ? 'Đã Đánh Giá Tất Cả' : 'Gửi Đánh Giá'}
            </button>
            </Modal.Body>
        </Modal>
    );
}


export default ModalFeedBack;
