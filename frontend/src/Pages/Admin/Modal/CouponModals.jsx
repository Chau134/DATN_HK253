import React, { useContext, useEffect, useState } from 'react';
import classNames from 'classnames/bind';
import request, { getApiError } from '../../../config/Connect';
import { fetchAdminCustomers } from '../../../api/adminCustomerApi';
import styles from './Modal.module.scss';

const cx = classNames.bind(styles);
const ModalContext = React.createContext({ onHide: () => {} });

// Custom Modal Components matching other admin modals
function ModalRoot({ show, onHide, size, children, contentClassName }) {
    if (!show) return null;
    const dialogSizeClass = size ? `modal-${size}` : '';
    return (
        <ModalContext.Provider value={{ onHide }}>
            <div className="modal fade show d-block" tabIndex="-1" role="dialog" aria-modal="true">
                <div className={`modal-dialog modal-dialog-centered ${dialogSizeClass}`} role="document">
                    <div className={`modal-content ${contentClassName || ''}`}>{children}</div>
                </div>
            </div>
            <div className="modal-backdrop fade show" />
        </ModalContext.Provider>
    );
}

function ModalHeader({ closeButton, children }) {
    const { onHide } = useContext(ModalContext);
    return (
        <div className="modal-header">
            {children}
            {closeButton && <button type="button" className="btn-close" aria-label="Đóng" onClick={onHide} />}
        </div>
    );
}

function ModalTitle({ children }) {
    return <h5 className="modal-title">{children}</h5>;
}

function ModalBody({ className, children }) {
    return <div className={`modal-body ${className || ''}`.trim()}>{children}</div>;
}

function ModalFooter({ children }) {
    return <div className="modal-footer">{children}</div>;
}

function Button({ variant = 'primary', onClick, disabled, children }) {
    return (
        <button type="button" className={`btn btn-${variant}`} onClick={onClick} disabled={disabled}>
            {children}
        </button>
    );
}

const Modal = Object.assign(ModalRoot, {
    Header: ModalHeader,
    Title: ModalTitle,
    Body: ModalBody,
    Footer: ModalFooter,
});

const emptyCouponForm = {
    code: '',
    name: '',
    description: '',
    discountType: 'PERCENTAGE',
    discountValue: '',
    maxDiscountAmount: '',
    minOrderAmount: '0',
    currency: 'VND',
    usageLimit: '',
    usageLimitPerUser: '',
    status: 'ACTIVE',
    customerScope: 'ALL',
    eligibleUserAccountId: '',
    customerSegment: '',
    startsAt: '',
    endsAt: '',
};

function toDateTimeLocalValue(value) {
    if (!value) return '';
    const date = new Date(value);
    if (isNaN(date.getTime())) return '';
    const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return localDate.toISOString().slice(0, 16);
}

function toInstantValue(value) {
    return value ? new Date(value).toISOString() : null;
}

function numberOrNull(value) {
    if (value === '' || value === null || value === undefined) return null;
    const num = Number(value);
    return isFinite(num) ? num : null;
}

// =================== ADD COUPON ===================
export function ModalAddCoupon({ show, setShow, onChanged }) {
    const handleClose = () => setShow(false);
    const [form, setForm] = useState(emptyCouponForm);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [customers, setCustomers] = useState([]);

    useEffect(() => {
        if (show) {
            setForm(emptyCouponForm);
            setError('');
            fetchAdminCustomers()
                .then(data => setCustomers(data || []))
                .catch(err => console.error('Error fetching customers', err));
        }
    }, [show]);

    const updateForm = (field, val) => setForm((cur) => ({ ...cur, [field]: val }));

    const handleAdd = async () => {
        if (!form.code.trim()) {
            setError('Mã coupon không được bỏ trống');
            return;
        }
        if (!form.name.trim()) {
            setError('Tên chương trình không được bỏ trống');
            return;
        }
        if (!form.discountValue || Number(form.discountValue) <= 0) {
            setError('Giá trị giảm giá phải lớn hơn 0');
            return;
        }

        try {
            setSaving(true);
            setError('');
            const payload = {
                code: form.code.trim().toUpperCase(),
                name: form.name.trim(),
                description: form.description.trim() || null,
                discount_type: form.discountType,
                discount_value: Number(form.discountValue),
                max_discount_amount: numberOrNull(form.maxDiscountAmount),
                min_order_amount: Number(form.minOrderAmount || 0),
                currency: form.currency,
                usage_limit: numberOrNull(form.usageLimit),
                usage_limit_per_user: numberOrNull(form.usageLimitPerUser),
                status: form.status,
                customer_scope: form.customerScope,
                eligible_user_account_id: form.customerScope === 'SPECIFIC_CUSTOMER' ? numberOrNull(form.eligibleUserAccountId) : null,
                customer_segment: form.customerSegment.trim() || null,
                starts_at: toInstantValue(form.startsAt),
                ends_at: toInstantValue(form.endsAt),
            };

            await request.post('/admin/coupons', payload);
            await onChanged?.();
            handleClose();
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi tạo mã giảm giá'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Thêm Mã Giảm Giá</Modal.Title>
            </Modal.Header>
            <Modal.Body className={cx('product-edit-body')}>
                <div className={cx('product-edit-box-title')}>
                    <h4>Thêm Mã Giảm Giá Mới</h4>
                </div>
                {error && <div className="alert alert-danger">{error}</div>}
                <section className={cx('product-edit-section')}>
                    <h5>Thông tin chung</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>Mã Coupon (Ví dụ: GIAM30K)
                            <input type="text" className="form-control" value={form.code} onChange={(e) => updateForm('code', e.target.value.toUpperCase())} />
                        </label>
                        <label>Tên chương trình
                            <input type="text" className="form-control" value={form.name} onChange={(e) => updateForm('name', e.target.value)} />
                        </label>
                    </div>
                    <label>Mô tả chi tiết
                        <textarea className="form-control" value={form.description} onChange={(e) => updateForm('description', e.target.value)} />
                    </label>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Cấu hình giảm giá</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>Loại hình giảm
                            <select className="form-select" value={form.discountType} onChange={(e) => updateForm('discountType', e.target.value)}>
                                <option value="PERCENTAGE">Phần trăm (%)</option>
                                <option value="FIXED_AMOUNT">Số tiền cố định (VND)</option>
                                <option value="FREE_SHIPPING">Miễn phí vận chuyển</option>
                            </select>
                        </label>
                        <label>Giá trị giảm
                            <input type="number" className="form-control" value={form.discountValue} onChange={(e) => updateForm('discountValue', e.target.value)} />
                        </label>
                        <label>Số tiền giảm tối đa (nếu %/free ship)
                            <input type="number" className="form-control" value={form.maxDiscountAmount} onChange={(e) => updateForm('maxDiscountAmount', e.target.value)} />
                        </label>
                        <label>Đơn hàng tối thiểu
                            <input type="number" className="form-control" value={form.minOrderAmount} onChange={(e) => updateForm('minOrderAmount', e.target.value)} />
                        </label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Giới hạn sử dụng & Trạng thái</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>Tổng lượt sử dụng tối đa
                            <input type="number" className="form-control" placeholder="Không giới hạn" value={form.usageLimit} onChange={(e) => updateForm('usageLimit', e.target.value)} />
                        </label>
                        <label>Lượt sử dụng tối đa / User
                            <input type="number" className="form-control" placeholder="Không giới hạn" value={form.usageLimitPerUser} onChange={(e) => updateForm('usageLimitPerUser', e.target.value)} />
                        </label>
                        <label>Trạng thái ban đầu
                            <select className="form-select" value={form.status} onChange={(e) => updateForm('status', e.target.value)}>
                                <option value="ACTIVE">ACTIVE (Kích hoạt)</option>
                                <option value="DRAFT">DRAFT (Bản nháp)</option>
                                <option value="PAUSED">PAUSED (Tạm ngưng)</option>
                            </select>
                        </label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Đối tượng & Thời gian hiệu lực</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>Đối tượng khách hàng
                            <select className="form-select" value={form.customerScope} onChange={(e) => updateForm('customerScope', e.target.value)}>
                                <option value="ALL">Tất cả khách hàng</option>
                                <option value="SPECIFIC_CUSTOMER">Khách hàng cụ thể (Chỉ định)</option>
                            </select>
                        </label>
                        {form.customerScope === 'SPECIFIC_CUSTOMER' && (
                            <label>Chọn khách hàng chỉ định
                                <select 
                                    className="form-select" 
                                    value={form.eligibleUserAccountId} 
                                    onChange={(e) => updateForm('eligibleUserAccountId', e.target.value)}
                                >
                                    <option value="">-- Chọn khách hàng --</option>
                                    {customers.map(c => (
                                        <option key={c.id} value={c.id}>
                                            {c.full_name || c.display_name || 'Khách hàng'} ({c.email}) - ID: {c.id}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        )}
                        <label>Hiệu lực từ lúc
                            <input type="datetime-local" className="form-control" value={form.startsAt} onChange={(e) => updateForm('startsAt', e.target.value)} />
                        </label>
                        <label>Hết hạn lúc
                            <input type="datetime-local" className="form-control" value={form.endsAt} onChange={(e) => updateForm('endsAt', e.target.value)} />
                        </label>
                    </div>
                </section>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose}>Đóng</Button>
                <Button variant="primary" onClick={handleAdd} disabled={saving}>{saving ? 'Đang tạo...' : 'Tạo mới'}</Button>
            </Modal.Footer>
        </Modal>
    );
}

// =================== EDIT COUPON ===================
export function ModalEditCoupon({ show, setShow, couponId, onChanged }) {
    const handleClose = () => setShow(false);
    const [form, setForm] = useState(emptyCouponForm);
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [customers, setCustomers] = useState([]);

    useEffect(() => {
        if (show && couponId) {
            setError('');
            setLoading(true);
            
            fetchAdminCustomers()
                .then(data => setCustomers(data || []))
                .catch(err => console.error('Error fetching customers', err));

            request.get(`/admin/coupons/${couponId}`)
                .then((res) => {
                    const data = res.data;
                    setForm({
                        code: data.code ?? '',
                        name: data.name ?? '',
                        description: data.description ?? '',
                        discountType: data.discount_type ?? 'PERCENTAGE',
                        discountValue: data.discount_value ?? '',
                        maxDiscountAmount: data.max_discount_amount ?? '',
                        minOrderAmount: data.min_order_amount ?? '0',
                        currency: data.currency ?? 'VND',
                        usageLimit: data.usage_limit ?? '',
                        usageLimitPerUser: data.usage_limit_per_user ?? '',
                        status: data.status ?? 'ACTIVE',
                        customerScope: data.customer_scope ?? 'ALL',
                        eligibleUserAccountId: data.eligible_user_account_id ?? '',
                        customerSegment: data.customer_segment ?? '',
                        startsAt: toDateTimeLocalValue(data.starts_at),
                        endsAt: toDateTimeLocalValue(data.ends_at),
                    });
                })
                .catch((err) => setError(getApiError(err, 'Lỗi khi tải thông tin mã giảm giá')))
                .finally(() => setLoading(false));
        }
    }, [show, couponId]);

    const updateForm = (field, val) => setForm((cur) => ({ ...cur, [field]: val }));

    const handleEdit = async () => {
        if (!form.code.trim()) {
            setError('Mã coupon không được bỏ trống');
            return;
        }
        if (!form.name.trim()) {
            setError('Tên chương trình không được bỏ trống');
            return;
        }
        if (!form.discountValue || Number(form.discountValue) <= 0) {
            setError('Giá trị giảm giá phải lớn hơn 0');
            return;
        }

        try {
            setSaving(true);
            setError('');
            const payload = {
                code: form.code.trim().toUpperCase(),
                name: form.name.trim(),
                description: form.description.trim() || null,
                discount_type: form.discountType,
                discount_value: Number(form.discountValue),
                max_discount_amount: numberOrNull(form.maxDiscountAmount),
                min_order_amount: Number(form.minOrderAmount || 0),
                currency: form.currency,
                usage_limit: numberOrNull(form.usageLimit),
                usage_limit_per_user: numberOrNull(form.usageLimitPerUser),
                status: form.status,
                customer_scope: form.customerScope,
                eligible_user_account_id: form.customerScope === 'SPECIFIC_CUSTOMER' ? numberOrNull(form.eligibleUserAccountId) : null,
                customer_segment: form.customerSegment.trim() || null,
                starts_at: toInstantValue(form.startsAt),
                ends_at: toInstantValue(form.endsAt),
            };

            await request.put(`/admin/coupons/${couponId}`, payload);
            await onChanged?.();
            handleClose();
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi cập nhật mã giảm giá'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Sửa Mã Giảm Giá</Modal.Title>
            </Modal.Header>
            <Modal.Body className={cx('product-edit-body')}>
                {loading ? (
                    <div>Đang tải dữ liệu...</div>
                ) : (
                    <>
                        <div className={cx('product-edit-box-title')}>
                            <h4>Sửa Thông Tin Mã Giảm Giá</h4>
                        </div>
                        {error && <div className="alert alert-danger">{error}</div>}
                        <section className={cx('product-edit-section')}>
                            <h5>Thông tin chung</h5>
                            <div className={cx('product-edit-grid')}>
                                <label>Mã Coupon
                                    <input type="text" className="form-control" value={form.code} onChange={(e) => updateForm('code', e.target.value.toUpperCase())} />
                                </label>
                                <label>Tên chương trình
                                    <input type="text" className="form-control" value={form.name} onChange={(e) => updateForm('name', e.target.value)} />
                                </label>
                            </div>
                            <label>Mô tả chi tiết
                                <textarea className="form-control" value={form.description} onChange={(e) => updateForm('description', e.target.value)} />
                            </label>
                        </section>

                        <section className={cx('product-edit-section')}>
                            <h5>Cấu hình giảm giá</h5>
                            <div className={cx('product-edit-grid')}>
                                <label>Loại hình giảm
                                    <select className="form-select" value={form.discountType} onChange={(e) => updateForm('discountType', e.target.value)}>
                                        <option value="PERCENTAGE">Phần trăm (%)</option>
                                        <option value="FIXED_AMOUNT">Số tiền cố định (VND)</option>
                                        <option value="FREE_SHIPPING">Miễn phí vận chuyển</option>
                                    </select>
                                </label>
                                <label>Giá trị giảm
                                    <input type="number" className="form-control" value={form.discountValue} onChange={(e) => updateForm('discountValue', e.target.value)} />
                                </label>
                                <label>Số tiền giảm tối đa (nếu %/free ship)
                                    <input type="number" className="form-control" value={form.maxDiscountAmount} onChange={(e) => updateForm('maxDiscountAmount', e.target.value)} />
                                </label>
                                <label>Đơn hàng tối thiểu
                                    <input type="number" className="form-control" value={form.minOrderAmount} onChange={(e) => updateForm('minOrderAmount', e.target.value)} />
                                </label>
                            </div>
                        </section>

                        <section className={cx('product-edit-section')}>
                            <h5>Giới hạn sử dụng & Trạng thái</h5>
                            <div className={cx('product-edit-grid')}>
                                <label>Tổng lượt sử dụng tối đa
                                    <input type="number" className="form-control" placeholder="Không giới hạn" value={form.usageLimit} onChange={(e) => updateForm('usageLimit', e.target.value)} />
                                </label>
                                <label>Lượt sử dụng tối đa / User
                                    <input type="number" className="form-control" placeholder="Không giới hạn" value={form.usageLimitPerUser} onChange={(e) => updateForm('usageLimitPerUser', e.target.value)} />
                                </label>
                                <label>Trạng thái
                                    <select className="form-select" value={form.status} onChange={(e) => updateForm('status', e.target.value)}>
                                        <option value="ACTIVE">ACTIVE (Kích hoạt)</option>
                                        <option value="DRAFT">DRAFT (Bản nháp)</option>
                                        <option value="PAUSED">PAUSED (Tạm ngưng)</option>
                                        <option value="EXPIRED">EXPIRED (Hết hạn)</option>
                                        <option value="ARCHIVED">ARCHIVED (Lưu trữ)</option>
                                    </select>
                                </label>
                            </div>
                        </section>

                        <section className={cx('product-edit-section')}>
                            <h5>Đối tượng & Thời gian hiệu lực</h5>
                            <div className={cx('product-edit-grid')}>
                                <label>Đối tượng khách hàng
                                    <select className="form-select" value={form.customerScope} onChange={(e) => updateForm('customerScope', e.target.value)}>
                                        <option value="ALL">Tất cả khách hàng</option>
                                        <option value="SPECIFIC_CUSTOMER">Khách hàng cụ thể (Chỉ định)</option>
                                    </select>
                                </label>
                                {form.customerScope === 'SPECIFIC_CUSTOMER' && (
                                    <label>Chọn khách hàng chỉ định
                                        <select 
                                            className="form-select" 
                                            value={form.eligibleUserAccountId} 
                                            onChange={(e) => updateForm('eligibleUserAccountId', e.target.value)}
                                        >
                                            <option value="">-- Chọn khách hàng --</option>
                                            {customers.map(c => (
                                                <option key={c.id} value={c.id}>
                                                    {c.full_name || c.display_name || 'Khách hàng'} ({c.email}) - ID: {c.id}
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                )}
                                <label>Hiệu lực từ lúc
                                    <input type="datetime-local" className="form-control" value={form.startsAt} onChange={(e) => updateForm('startsAt', e.target.value)} />
                                </label>
                                <label>Hết hạn lúc
                                    <input type="datetime-local" className="form-control" value={form.endsAt} onChange={(e) => updateForm('endsAt', e.target.value)} />
                                </label>
                            </div>
                        </section>
                    </>
                )}
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose}>Đóng</Button>
                <Button variant="primary" onClick={handleEdit} disabled={saving || loading}>{saving ? 'Đang lưu...' : 'Lưu thay đổi'}</Button>
            </Modal.Footer>
        </Modal>
    );
}

// =================== DELETE / ARCHIVE COUPON ===================
export function ModalDeleteCoupon({ show, setShow, couponId, onChanged }) {
    const handleClose = () => setShow(false);
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (show) {
            setError('');
        }
    }, [show]);

    const handleDelete = async () => {
        if (!window.confirm(`Xác nhận lần 2: lưu trữ/xóa chính thức mã giảm giá có ID ${couponId}?`)) {
            return;
        }

        try {
            setDeleting(true);
            setError('');
            await request.delete(`/admin/coupons/${couponId}`);
            await onChanged?.();
            handleClose();
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi lưu trữ mã giảm giá'));
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose}>
            <Modal.Header closeButton>
                <Modal.Title>Lưu Trữ Mã Giảm Giá</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <div className={cx('product-edit-box-title')}>
                    <h4>Xác nhận lưu trữ</h4>
                    <p>Bạn chắc chắn muốn lưu trữ (vô hiệu hóa) mã giảm giá có ID: <strong>{couponId}</strong>?</p>
                    <p className="text-muted small">Sau khi lưu trữ, mã giảm giá sẽ không thể sử dụng ở trang thanh toán nữa.</p>
                </div>
                {error && <div className="alert alert-danger">{error}</div>}
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose} disabled={deleting}>Đóng</Button>
                <Button variant="danger" onClick={handleDelete} disabled={deleting}>
                    {deleting ? 'Đang lưu trữ...' : 'Xác nhận'}
                </Button>
            </Modal.Footer>
        </Modal>
    );
}
