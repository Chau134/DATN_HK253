import React, { useEffect, useState, useCallback } from 'react';
import classNames from 'classnames/bind';
import request from '../../../../../config/Connect';
import styles from './Promotions.module.scss';
import {
    ModalAddPromotion,
    ModalEditPromotion,
    ModalDeletePromotion,
    ModalManagePromotionTargets
} from '../../../Modal/Modal';

const cx = classNames.bind(styles);
const tableTextStyle = { color: '#fff' };

function formatPrice(value) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        maximumFractionDigits: 0,
    }).format(Number(value || 0));
}

function formatDate(isoString) {
    if (!isoString) return 'Vô thời hạn';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return 'Sai định dạng';
    return date.toLocaleString('vi-VN');
}

function getDiscountTypeLabel(type) {
    const map = {
        PERCENTAGE: 'Phần trăm (%)',
        FIXED_AMOUNT: 'Số tiền cố định',
        FREE_SHIPPING: 'Miễn phí vận chuyển'
    };
    return map[type] || type;
}

function getCustomerScopeLabel(scope) {
    const map = {
        ALL: 'Tất cả khách hàng',
        SPECIFIC_CUSTOMER: 'Khách hàng cụ thể'
    };
    return map[scope] || scope;
}

function Promotions() {
    const [promotions, setPromotions] = useState([]);
    const [statusFilter, setStatusFilter] = useState('ACTIVE');
    const [loading, setLoading] = useState(false);

    // Modals visibility states
    const [showAdd, setShowAdd] = useState(false);
    const [showEdit, setShowEdit] = useState(false);
    const [showDelete, setShowDelete] = useState(false);
    const [showManageTargets, setShowManageTargets] = useState(false);

    // Selected promotion details
    const [selectedId, setSelectedId] = useState(null);

    const fetchPromotions = useCallback(async () => {
        setLoading(true);
        try {
            const endpoint = statusFilter ? `/admin/promotions?status=${statusFilter}` : '/admin/promotions';
            const response = await request.get(endpoint);
            setPromotions(response.data || []);
        } catch (error) {
            console.error('Lỗi khi lấy danh sách khuyến mãi:', error);
            setPromotions([]);
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        fetchPromotions();
    }, [fetchPromotions]);

    const handleShowAdd = () => setShowAdd(true);

    const handleShowEdit = (id) => {
        setSelectedId(id);
        setShowEdit(true);
    };

    const handleShowDelete = (id) => {
        setSelectedId(id);
        setShowDelete(true);
    };

    const handleShowManageTargets = (id) => {
        setSelectedId(id);
        setShowManageTargets(true);
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('header-promotions')}>
                <h1>Quản Lý Khuyến Mãi</h1>
                <button onClick={handleShowAdd} type="button" className="btn btn-primary">
                    Thêm Khuyến Mãi
                </button>
            </div>

            <div className="mb-3 d-flex align-items-center gap-2">
                <span style={{ color: '#fff', fontWeight: 600 }}>Lọc trạng thái:</span>
                <select
                    className="form-select"
                    style={{ width: '280px' }}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    value={statusFilter}
                    disabled={loading}
                >
                    <option value="">Tất cả</option>
                    <option value="ACTIVE">ACTIVE (Đang hoạt động)</option>
                    <option value="ARCHIVED">ARCHIVED (Đã lưu trữ)</option>
                </select>
            </div>

            {loading ? (
                <div className="text-white">Đang tải danh sách khuyến mãi...</div>
            ) : promotions.length === 0 ? (
                <div className="text-white">Không tìm thấy chương trình khuyến mãi nào</div>
            ) : (
                <table className={cx('promotions-table')}>
                    <thead>
                        <tr>
                            <th style={tableTextStyle}>ID</th>
                            <th style={tableTextStyle}>Tên Chương Trình</th>
                            <th style={tableTextStyle}>Loại Giảm</th>
                            <th style={tableTextStyle}>Giá Trị</th>
                            <th style={tableTextStyle}>Đơn Tối Thiểu</th>
                            <th style={tableTextStyle}>Cộng Dồn</th>
                            <th style={tableTextStyle}>Đối Tượng</th>
                            <th style={tableTextStyle}>Hiệu Lực</th>
                            <th style={tableTextStyle}>Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {promotions.map((item) => (
                            <tr key={item.id}>
                                <th style={tableTextStyle}>{item.id}</th>
                                <td style={tableTextStyle}>
                                    <div className={cx('promo-name')}>{item.name}</div>
                                    {item.description && (
                                        <div className={cx('promo-desc')}>{item.description}</div>
                                    )}
                                </td>
                                <td style={tableTextStyle}>{getDiscountTypeLabel(item.discount_type)}</td>
                                <td style={tableTextStyle}>
                                    {item.discount_type === 'PERCENTAGE'
                                        ? `${item.discount_value}% (Tối đa ${item.max_discount_amount ? formatPrice(item.max_discount_amount) : 'Không giới hạn'})`
                                        : formatPrice(item.discount_value)}
                                </td>
                                <td style={tableTextStyle}>{formatPrice(item.min_order_amount)}</td>
                                <td style={tableTextStyle}>{item.stackable ? 'Có' : 'Không'}</td>
                                <td style={tableTextStyle}>
                                    {getCustomerScopeLabel(item.customer_scope)}
                                    {item.customer_scope === 'SPECIFIC_CUSTOMER' && item.eligible_user_account_id && (
                                        <span className="badge bg-secondary ms-1">ID: {item.eligible_user_account_id}</span>
                                    )}
                                </td>
                                <td style={tableTextStyle} className={cx('promo-date')}>
                                    <div>Bắt đầu: {formatDate(item.starts_at)}</div>
                                    <div>Kết thúc: {formatDate(item.ends_at)}</div>
                                </td>
                                <td className={cx('actions')} style={tableTextStyle}>
                                    <button
                                        onClick={() => handleShowManageTargets(item.id)}
                                        type="button"
                                        className="btn btn-info text-white"
                                        title="Quản lý áp dụng cho Sản phẩm & Danh mục"
                                    >
                                        Áp Dụng
                                    </button>
                                    <button
                                        onClick={() => handleShowEdit(item.id)}
                                        type="button"
                                        className="btn btn-warning"
                                    >
                                        Sửa
                                    </button>
                                    {item.status === 'ACTIVE' && (
                                        <button
                                            onClick={() => handleShowDelete(item.id)}
                                            type="button"
                                            className="btn btn-danger"
                                        >
                                            Xóa/Lưu trữ
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            <ModalAddPromotion
                show={showAdd}
                setShow={setShowAdd}
                onChanged={fetchPromotions}
            />
            <ModalEditPromotion
                show={showEdit}
                setShow={setShowEdit}
                promotionId={selectedId}
                onChanged={fetchPromotions}
            />
            <ModalDeletePromotion
                show={showDelete}
                setShow={setShowDelete}
                promotionId={selectedId}
                onChanged={fetchPromotions}
            />
            <ModalManagePromotionTargets
                show={showManageTargets}
                setShow={setShowManageTargets}
                promotionId={selectedId}
            />
        </div>
    );
}

export default Promotions;
