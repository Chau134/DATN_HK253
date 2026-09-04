import React, { useEffect, useState, useCallback } from 'react';
import classNames from 'classnames/bind';
import request from '../../../../../config/Connect';
import styles from './Coupons.module.scss';
import {
    ModalAddCoupon,
    ModalEditCoupon,
    ModalDeleteCoupon
} from '../../../Modal/Modal';

const cx = classNames.bind(styles);
const tableTextStyle = { color: '#fff' };

function formatPriceAdmin(value) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        maximumFractionDigits: 0,
    }).format(Number(value || 0));
}

function formatPriceCustomer(value) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        maximumFractionDigits: 0,
    }).format(Number(value || 0) * 1000);
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

function publishNotification(coupon) {
    const currentNotifs = JSON.parse(localStorage.getItem('mystery_closet_notifications') || '[]');
    
    // Check if notification for this coupon code already exists to avoid duplication if clicked multiple times
    const exists = currentNotifs.some(n => n.coupon_code === coupon.code);
    if (exists) {
        if (!window.confirm(`Thông báo cho mã ${coupon.code} đã tồn tại. Bạn có muốn gửi thêm một thông báo mới không?`)) {
            return false;
        }
    }

    const newNotif = {
        id: `notif_${Date.now()}_${coupon.id}`,
        title: `🎁 Nhận ngay mã giảm giá ${coupon.code}!`,
        message: `Admin gửi tặng bạn mã giảm giá: ${coupon.name}. Giảm ${coupon.discount_type === 'PERCENTAGE' ? `${coupon.discount_value}%` : formatPriceCustomer(coupon.discount_value)} cho đơn hàng từ ${formatPriceCustomer(coupon.min_order_amount)}.${coupon.ends_at ? ` Hạn dùng đến: ${formatDate(coupon.ends_at)}.` : ''}`,
        coupon_code: coupon.code,
        created_at: new Date().toISOString(),
        read: false
    };
    
    localStorage.setItem('mystery_closet_notifications', JSON.stringify([newNotif, ...currentNotifs]));
    
    // Trigger instant UI updates if user tab is open in same browser
    window.dispatchEvent(new CustomEvent('notifications:changed'));
    return true;
}

function Coupons() {
    const [coupons, setCoupons] = useState([]);
    const [statusFilter, setStatusFilter] = useState('ACTIVE');
    const [loading, setLoading] = useState(false);

    // Modals visibility
    const [showAdd, setShowAdd] = useState(false);
    const [showEdit, setShowEdit] = useState(false);
    const [showDelete, setShowDelete] = useState(false);

    // Selected coupon
    const [selectedId, setSelectedId] = useState(null);

    const fetchCoupons = useCallback(async () => {
        setLoading(true);
        try {
            const endpoint = statusFilter ? `/admin/coupons?status=${statusFilter}` : '/admin/coupons';
            const response = await request.get(endpoint);
            setCoupons(response.data || []);
        } catch (error) {
            console.error('Lỗi khi lấy danh sách mã giảm giá:', error);
            setCoupons([]);
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        fetchCoupons();
    }, [fetchCoupons]);

    const handleShowAdd = () => setShowAdd(true);

    const handleShowEdit = (id) => {
        setSelectedId(id);
        setShowEdit(true);
    };

    const handleShowDelete = (id) => {
        setSelectedId(id);
        setShowDelete(true);
    };

    const handlePublishNotification = (coupon) => {
        try {
            const success = publishNotification(coupon);
            if (success) {
                alert(`Đã gửi thông báo về mã giảm giá ${coupon.code} tới khách hàng thành công!`);
            }
        } catch (err) {
            console.error(err);
            alert('Lỗi khi gửi thông báo mã giảm giá.');
        }
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('header-promotions')}>
                <h1>Quản Lý Mã Giảm Giá</h1>
                <button onClick={handleShowAdd} type="button" className="btn btn-primary">
                    Thêm Mã Giảm Giá
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
                    <option value="DRAFT">DRAFT (Bản nháp)</option>
                    <option value="PAUSED">PAUSED (Tạm ngưng)</option>
                    <option value="EXPIRED">EXPIRED (Hết hạn)</option>
                    <option value="ARCHIVED">ARCHIVED (Đã lưu trữ)</option>
                </select>
            </div>

            {loading ? (
                <div className="text-white">Đang tải danh sách mã giảm giá...</div>
            ) : coupons.length === 0 ? (
                <div className="text-white">Không tìm thấy mã giảm giá nào</div>
            ) : (
                <table className={cx('promotions-table')}>
                    <thead>
                        <tr>
                            <th style={tableTextStyle}>ID</th>
                            <th style={tableTextStyle}>Mã Code</th>
                            <th style={tableTextStyle}>Tên / Mô tả</th>
                            <th style={tableTextStyle}>Loại Giảm</th>
                            <th style={tableTextStyle}>Giá Trị Giảm</th>
                            <th style={tableTextStyle}>Đơn Tối Thiểu</th>
                            <th style={tableTextStyle}>Đã Dùng / Giới Hạn</th>
                            <th style={tableTextStyle}>Đối Tượng</th>
                            <th style={tableTextStyle}>Hiệu Lực</th>
                            <th style={tableTextStyle}>Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {coupons.map((item) => (
                            <tr key={item.id}>
                                <th style={tableTextStyle}>{item.id}</th>
                                <td style={tableTextStyle}>
                                    <strong className="badge bg-primary fs-6">{item.code}</strong>
                                </td>
                                <td style={tableTextStyle}>
                                    <div className={cx('promo-name')}>{item.name}</div>
                                    {item.description && (
                                        <div className={cx('promo-desc')}>{item.description}</div>
                                    )}
                                </td>
                                <td style={tableTextStyle}>{getDiscountTypeLabel(item.discount_type)}</td>
                                <td style={tableTextStyle}>
                                    {item.discount_type === 'PERCENTAGE'
                                        ? `${item.discount_value}% (Tối đa ${item.max_discount_amount ? formatPriceAdmin(item.max_discount_amount) : 'Không giới hạn'})`
                                        : formatPriceAdmin(item.discount_value)}
                                </td>
                                <td style={tableTextStyle}>{formatPriceAdmin(item.min_order_amount)}</td>
                                <td style={tableTextStyle}>
                                    {item.used_count} / {item.usage_limit || 'Không giới hạn'}
                                    {item.usage_limit_per_user && (
                                        <div className="text-muted small">(Max {item.usage_limit_per_user}/khách)</div>
                                    )}
                                </td>
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
                                    {item.status === 'ACTIVE' && (
                                        <button
                                            onClick={() => handlePublishNotification(item)}
                                            type="button"
                                            className="btn btn-success text-white"
                                            title="Gửi thông báo mã giảm giá tới khách hàng"
                                        >
                                            Gửi Thông Báo
                                        </button>
                                    )}
                                    <button
                                        onClick={() => handleShowEdit(item.id)}
                                        type="button"
                                        className="btn btn-warning"
                                    >
                                        Sửa
                                    </button>
                                    {item.status !== 'ARCHIVED' && (
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

            <ModalAddCoupon
                show={showAdd}
                setShow={setShowAdd}
                onChanged={fetchCoupons}
            />
            <ModalEditCoupon
                show={showEdit}
                setShow={setShowEdit}
                couponId={selectedId}
                onChanged={fetchCoupons}
            />
            <ModalDeleteCoupon
                show={showDelete}
                setShow={setShowDelete}
                couponId={selectedId}
                onChanged={fetchCoupons}
            />
        </div>
    );
}

export default Coupons;
