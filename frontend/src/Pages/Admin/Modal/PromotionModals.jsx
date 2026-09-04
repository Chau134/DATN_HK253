import React, { useContext, useEffect, useState } from 'react';
import classNames from 'classnames/bind';
import request, { getApiError } from '../../../config/Connect';
import { fetchAdminProducts, fetchAdminCategories } from '../../../api/adminCatalogApi';
import styles from './Modal.module.scss';

const cx = classNames.bind(styles);
const ModalContext = React.createContext({ onHide: () => {} });

// Reusable Custom Modal Components (Matching ProductModals.jsx exactly)
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

const emptyPromotionForm = {
    name: '',
    description: '',
    discountType: 'PERCENTAGE',
    discountValue: '',
    maxDiscountAmount: '',
    minOrderAmount: '0',
    currency: 'VND',
    status: 'ACTIVE',
    priority: '0',
    stackable: false,
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

// =================== ADD PROMOTION ===================
export function ModalAddPromotion({ show, setShow, onChanged }) {
    const handleClose = () => setShow(false);
    const [form, setForm] = useState(emptyPromotionForm);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (show) {
            setForm(emptyPromotionForm);
            setError('');
        }
    }, [show]);

    const updateForm = (field, val) => setForm((cur) => ({ ...cur, [field]: val }));

    const handleAdd = async () => {
        if (!form.name.trim()) {
            setError('Tên khuyến mãi không được bỏ trống');
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
                name: form.name.trim(),
                description: form.description.trim() || null,
                discount_type: form.discountType,
                discount_value: Number(form.discountValue),
                max_discount_amount: numberOrNull(form.maxDiscountAmount),
                min_order_amount: Number(form.minOrderAmount || 0),
                currency: form.currency,
                status: form.status,
                priority: Number(form.priority || 0),
                stackable: form.stackable,
                customer_scope: form.customerScope,
                eligible_user_account_id: form.customerScope === 'SPECIFIC_CUSTOMER' ? numberOrNull(form.eligibleUserAccountId) : null,
                customer_segment: form.customerSegment.trim() || null,
                starts_at: toInstantValue(form.startsAt),
                ends_at: toInstantValue(form.endsAt),
            };

            await request.post('/admin/promotions', payload);
            await onChanged?.();
            handleClose();
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi thêm khuyến mãi'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Thêm Chương Trình Khuyến Mãi</Modal.Title>
            </Modal.Header>
            <Modal.Body className={cx('product-edit-body')}>
                <div className={cx('product-edit-box-title')}>
                    <h4>Thêm Chương Trình Khuyến Mãi</h4>
                </div>
                {error && <div className="alert alert-danger">{error}</div>}
                <section className={cx('product-edit-section')}>
                    <h5>Thông tin khuyến mãi</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>Tên chương trình<input type="text" className="form-control" value={form.name} onChange={(e) => updateForm('name', e.target.value)} /></label>
                        <label>Mức ưu tiên (priority)<input type="number" className="form-control" value={form.priority} onChange={(e) => updateForm('priority', e.target.value)} /></label>
                    </div>
                    <label>Mô tả chương trình<textarea className="form-control" value={form.description} onChange={(e) => updateForm('description', e.target.value)} /></label>
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
                        <label>Giá trị giảm<input type="number" className="form-control" value={form.discountValue} onChange={(e) => updateForm('discountValue', e.target.value)} /></label>
                        <label>Số tiền giảm tối đa (nếu %)<input type="number" className="form-control" value={form.maxDiscountAmount} onChange={(e) => updateForm('maxDiscountAmount', e.target.value)} /></label>
                        <label>Đơn tối thiểu<input type="number" className="form-control" value={form.minOrderAmount} onChange={(e) => updateForm('minOrderAmount', e.target.value)} /></label>
                    </div>
                    <div className={cx('form-checkbox')} style={{ marginTop: '10px' }}>
                        <label><input type="checkbox" checked={form.stackable} onChange={(e) => updateForm('stackable', e.target.checked)} /> Cho phép cộng dồn (Stackable)</label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Đối tượng & Thời gian</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>Áp dụng cho
                            <select className="form-select" value={form.customerScope} onChange={(e) => updateForm('customerScope', e.target.value)}>
                                <option value="ALL">Tất cả khách hàng</option>
                                <option value="SPECIFIC_CUSTOMER">Khách hàng chỉ định</option>
                            </select>
                        </label>
                        {form.customerScope === 'SPECIFIC_CUSTOMER' && (
                            <label>ID Tài khoản khách hàng<input type="number" className="form-control" value={form.eligibleUserAccountId} onChange={(e) => updateForm('eligibleUserAccountId', e.target.value)} /></label>
                        )}
                        <label>Bắt đầu lúc<input type="datetime-local" className="form-control" value={form.startsAt} onChange={(e) => updateForm('startsAt', e.target.value)} /></label>
                        <label>Kết thúc lúc<input type="datetime-local" className="form-control" value={form.endsAt} onChange={(e) => updateForm('endsAt', e.target.value)} /></label>
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

// =================== EDIT PROMOTION ===================
export function ModalEditPromotion({ show, setShow, promotionId, onChanged }) {
    const handleClose = () => setShow(false);
    const [form, setForm] = useState(emptyPromotionForm);
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (show && promotionId) {
            setError('');
            setLoading(true);
            request.get(`/admin/promotions/${promotionId}`)
                .then((res) => {
                    const data = res.data;
                    setForm({
                        name: data.name ?? '',
                        description: data.description ?? '',
                        discountType: data.discount_type ?? 'PERCENTAGE',
                        discountValue: data.discount_value ?? '',
                        maxDiscountAmount: data.max_discount_amount ?? '',
                        minOrderAmount: data.min_order_amount ?? '0',
                        currency: data.currency ?? 'VND',
                        status: data.status ?? 'ACTIVE',
                        priority: data.priority ?? '0',
                        stackable: data.stackable ?? false,
                        customerScope: data.customer_scope ?? 'ALL',
                        eligibleUserAccountId: data.eligible_user_account_id ?? '',
                        customerSegment: data.customer_segment ?? '',
                        startsAt: toDateTimeLocalValue(data.starts_at),
                        endsAt: toDateTimeLocalValue(data.ends_at),
                    });
                })
                .catch((err) => setError(getApiError(err, 'Lỗi khi tải thông tin khuyến mãi')))
                .finally(() => setLoading(false));
        }
    }, [show, promotionId]);

    const updateForm = (field, val) => setForm((cur) => ({ ...cur, [field]: val }));

    const handleEdit = async () => {
        if (!form.name.trim()) {
            setError('Tên khuyến mãi không được bỏ trống');
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
                name: form.name.trim(),
                description: form.description.trim() || null,
                discount_type: form.discountType,
                discount_value: Number(form.discountValue),
                max_discount_amount: numberOrNull(form.maxDiscountAmount),
                min_order_amount: Number(form.minOrderAmount || 0),
                currency: form.currency,
                status: form.status,
                priority: Number(form.priority || 0),
                stackable: form.stackable,
                customer_scope: form.customerScope,
                eligible_user_account_id: form.customerScope === 'SPECIFIC_CUSTOMER' ? numberOrNull(form.eligibleUserAccountId) : null,
                customer_segment: form.customerSegment.trim() || null,
                starts_at: toInstantValue(form.startsAt),
                ends_at: toInstantValue(form.endsAt),
            };

            await request.put(`/admin/promotions/${promotionId}`, payload);
            await onChanged?.();
            handleClose();
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi cập nhật khuyến mãi'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Sửa Chương Trình Khuyến Mãi</Modal.Title>
            </Modal.Header>
            <Modal.Body className={cx('product-edit-body')}>
                {loading ? (
                    <div>Đang tải dữ liệu...</div>
                ) : (
                    <>
                        <div className={cx('product-edit-box-title')}>
                            <h4>Sửa Chương Trình Khuyến Mãi</h4>
                        </div>
                        {error && <div className="alert alert-danger">{error}</div>}
                        <section className={cx('product-edit-section')}>
                            <h5>Thông tin khuyến mãi</h5>
                            <div className={cx('product-edit-grid')}>
                                <label>Tên chương trình<input type="text" className="form-control" value={form.name} onChange={(e) => updateForm('name', e.target.value)} /></label>
                                <label>Mức ưu tiên (priority)<input type="number" className="form-control" value={form.priority} onChange={(e) => updateForm('priority', e.target.value)} /></label>
                            </div>
                            <label>Mô tả chương trình<textarea className="form-control" value={form.description} onChange={(e) => updateForm('description', e.target.value)} /></label>
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
                                <label>Giá trị giảm<input type="number" className="form-control" value={form.discountValue} onChange={(e) => updateForm('discountValue', e.target.value)} /></label>
                                <label>Số tiền giảm tối đa (nếu %)<input type="number" className="form-control" value={form.maxDiscountAmount} onChange={(e) => updateForm('maxDiscountAmount', e.target.value)} /></label>
                                <label>Đơn tối thiểu<input type="number" className="form-control" value={form.minOrderAmount} onChange={(e) => updateForm('minOrderAmount', e.target.value)} /></label>
                            </div>
                            <div className={cx('form-checkbox')} style={{ marginTop: '10px' }}>
                                <label><input type="checkbox" checked={form.stackable} onChange={(e) => updateForm('stackable', e.target.checked)} /> Cho phép cộng dồn (Stackable)</label>
                            </div>
                        </section>

                        <section className={cx('product-edit-section')}>
                            <h5>Đối tượng & Thời gian</h5>
                            <div className={cx('product-edit-grid')}>
                                <label>Áp dụng cho
                                    <select className="form-select" value={form.customerScope} onChange={(e) => updateForm('customerScope', e.target.value)}>
                                        <option value="ALL">Tất cả khách hàng</option>
                                        <option value="SPECIFIC_CUSTOMER">Khách hàng chỉ định</option>
                                    </select>
                                </label>
                                {form.customerScope === 'SPECIFIC_CUSTOMER' && (
                                    <label>ID Tài khoản khách hàng<input type="number" className="form-control" value={form.eligibleUserAccountId} onChange={(e) => updateForm('eligibleUserAccountId', e.target.value)} /></label>
                                )}
                                <label>Bắt đầu lúc<input type="datetime-local" className="form-control" value={form.startsAt} onChange={(e) => updateForm('startsAt', e.target.value)} /></label>
                                <label>Kết thúc lúc<input type="datetime-local" className="form-control" value={form.endsAt} onChange={(e) => updateForm('endsAt', e.target.value)} /></label>
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

// =================== DELETE / ARCHIVE PROMOTION ===================
export function ModalDeletePromotion({ show, setShow, promotionId, onChanged }) {
    const handleClose = () => setShow(false);
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (show) {
            setError('');
        }
    }, [show]);

    const handleDelete = async () => {
        if (!window.confirm(`Xác nhận lần 2: lưu trữ/xóa chính thức khuyến mãi có ID ${promotionId}?`)) {
            return;
        }

        try {
            setDeleting(true);
            setError('');
            await request.delete(`/admin/promotions/${promotionId}`);
            await onChanged?.();
            handleClose();
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi lưu trữ khuyến mãi'));
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose}>
            <Modal.Header closeButton>
                <Modal.Title>Lưu Trữ Khuyến Mãi</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <div className={cx('product-edit-box-title')}>
                    <h4>Xác nhận lưu trữ</h4>
                    <p>Bạn chắc chắn muốn lưu trữ (vô hiệu hóa) chương trình khuyến mãi có ID: <strong>{promotionId}</strong>?</p>
                    <p className="text-muted small">Sau khi lưu trữ, chương trình sẽ không được áp dụng tự động cho các đơn hàng nữa.</p>
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

const categoryNoiseWords = ['khuyen mai', 'giam gia', 'thanh ly', 'sale', 'ban hang', 'promotion', 'discount', 'clearance'];

function getCategoryLabel(category) {
    return (category?.label || category?.name_vi || category?.name || `Danh mục ${category?.id}`).toString().trim();
}

function normalizeCategoryOptionLabel(value) {
    if (!value) return '';
    const withoutDiacritics = value.normalize ? value.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : value;
    return withoutDiacritics
        .toLowerCase()
        .replace(/[_]+/g, ' ')
        .replace(/[^a-z0-9]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function buildCategoryOptions(list) {
    const seen = new Set();
    if (!Array.isArray(list)) return [];

    const options = [];
    for (const item of list) {
        const label = getCategoryLabel(item);
        const key = normalizeCategoryOptionLabel(label);
        const isCompoundLabel = /[,;]/.test(label);
        const isNoiseLabel = categoryNoiseWords.some((word) => key.includes(word));

        if (!label || !key || isCompoundLabel || isNoiseLabel || seen.has(item.id)) continue;
        seen.add(item.id);
        options.push({ ...item, id: item.id, label, value: String(item.id) });
    }

    return options;
}

function buildCategoryTree(categoriesList) {
    const idMap = {};
    const roots = [];

    categoriesList.forEach((cat) => {
        idMap[String(cat.value || cat.id)] = {
            ...cat,
            children: [],
        };
    });

    categoriesList.forEach((cat) => {
        const node = idMap[String(cat.value || cat.id)];
        const parentId = cat.parent_id || cat.parentId;
        if (parentId) {
            const parent = idMap[String(parentId)];
            if (parent) {
                parent.children.push(node);
            } else {
                roots.push(node);
            }
        } else {
            roots.push(node);
        }
    });

    return roots;
}

function filterTree(nodes, searchTerm) {
    if (!searchTerm) return nodes;
    const term = searchTerm.toLowerCase();

    const filter = (list) => {
        return list
            .map(node => {
                const matches = node.label.toLowerCase().includes(term);
                const filteredChildren = node.children ? filter(node.children) : [];
                if (matches || filteredChildren.length > 0) {
                    return {
                        ...node,
                        children: filteredChildren
                    };
                }
                return null;
            })
            .filter(Boolean);
    };

    return filter(nodes);
}

function CategoryTreeSelect({ nodes, selectedIds, onToggle, savingId, depth = 0 }) {
    if (!Array.isArray(nodes) || nodes.length === 0) return null;
    
    return (
        <>
            {nodes.map((node) => {
                const categoryId = Number(node.id);
                const collectDescendantIds = (n) => {
                    let ids = [Number(n.id)];
                    if (n.children) {
                        n.children.forEach(child => {
                            ids = ids.concat(collectDescendantIds(child));
                        });
                    }
                    return ids;
                };
                const allDescendantIds = collectDescendantIds(node);
                const isChecked = allDescendantIds.every(id => selectedIds.has(id));
                const isIndeterminate = !isChecked && allDescendantIds.some(id => selectedIds.has(id));
                const isSaving = savingId === `cat-${categoryId}`;
                return (
                    <div key={node.id} style={{ marginLeft: `${depth * 18}px` }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '2px 0', padding: '2px 0' }}>
                            <label className={cx('category-item')} style={{ display: 'flex', alignItems: 'center', margin: 0, cursor: 'pointer', flex: 1 }}>
                                <input
                                    type="checkbox"
                                    checked={isChecked}
                                    ref={el => {
                                        if (el) el.indeterminate = isIndeterminate;
                                    }}
                                    onChange={() => onToggle(categoryId)}
                                    disabled={savingId !== null}
                                    style={{ marginRight: '6px' }}
                                />
                                <span style={{ 
                                    fontWeight: depth === 0 ? '700' : depth === 1 ? '600' : '400',
                                    color: depth === 0 ? '#111' : depth === 1 ? '#333' : '#555',
                                    fontSize: depth === 0 ? '14px' : '13px'
                                }}>
                                    {depth > 0 ? '└─ ' : ''}{node.label}
                                </span>
                            </label>
                            {isSaving && <span className="spinner-border spinner-border-sm text-primary" style={{ marginLeft: '8px' }} />}
                        </div>
                        {node.children && node.children.length > 0 && (
                            <CategoryTreeSelect
                                nodes={node.children}
                                selectedIds={selectedIds}
                                onToggle={onToggle}
                                savingId={savingId}
                                depth={depth + 1}
                            />
                        )}
                    </div>
                );
            })}
        </>
    );
}

function getDescendantCategoryIds(catId, tree) {
    const findNode = (list, targetId) => {
        for (const node of list) {
            if (Number(node.id) === targetId) return node;
            if (node.children) {
                const found = findNode(node.children, targetId);
                if (found) return found;
            }
        }
        return null;
    };
    const collect = (node) => {
        let ids = [Number(node.id)];
        if (node.children) {
            node.children.forEach(child => {
                ids = ids.concat(collect(child));
            });
        }
        return ids;
    };
    const targetNode = findNode(tree, catId);
    return targetNode ? collect(targetNode) : [catId];
}

function collectProductsUnderCategory(catId, tree, productsByCat) {
    const findNode = (list, targetId) => {
        for (const node of list) {
            if (Number(node.id) === targetId) return node;
            if (node.children) {
                const found = findNode(node.children, targetId);
                if (found) return found;
            }
        }
        return null;
    };
    const collectIds = (node) => {
        const cId = Number(node.id);
        let products = (productsByCat[cId] || []).map(p => Number(p.id));
        if (node.children) {
            node.children.forEach(child => {
                products = products.concat(collectIds(child));
            });
        }
        return products;
    };
    const targetNode = findNode(tree, catId);
    if (!targetNode) return [];
    return Array.from(new Set(collectIds(targetNode)));
}

function filterTreeForProducts(nodes, productsByCategoryId) {
    const filter = (list) => {
        return list
            .map(node => {
                const categoryId = Number(node.id);
                const hasDirectProducts = (productsByCategoryId[categoryId] || []).length > 0;
                const filteredChildren = node.children ? filter(node.children) : [];
                if (hasDirectProducts || filteredChildren.length > 0) {
                    return {
                        ...node,
                        children: filteredChildren
                    };
                }
                return null;
            })
            .filter(Boolean);
    };

    return filter(nodes);
}

function ProductCategoryTreeSelect({ nodes, productsByCategoryId, selectedIds, onToggleProduct, onToggleCategoryProducts, savingId, depth = 0 }) {
    if (!Array.isArray(nodes) || nodes.length === 0) return null;

    return (
        <>
            {nodes.map((node) => {
                const categoryId = Number(node.id);
                const categoryProducts = productsByCategoryId[categoryId] || [];
                const hasChildren = node.children && node.children.length > 0;
                const hasProducts = categoryProducts.length > 0;

                const collectIds = (n) => {
                    const cId = Number(n.id);
                    let ids = (productsByCategoryId[cId] || []).map(p => Number(p.id));
                    if (n.children) {
                        n.children.forEach(child => {
                            ids = ids.concat(collectIds(child));
                        });
                    }
                    return ids;
                };
                const allProductIds = Array.from(new Set(collectIds(node)));
                
                const isChecked = allProductIds.length > 0 && allProductIds.every(id => selectedIds.has(id));
                const isIndeterminate = allProductIds.length > 0 && !isChecked && allProductIds.some(id => selectedIds.has(id));
                const isSaving = savingId === `cat-prod-${categoryId}`;

                return (
                    <div key={node.id} style={{ marginLeft: `${depth * 18}px`, marginBottom: '4px' }}>
                        <div style={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'space-between',
                            padding: '4px 0',
                            borderBottom: depth === 0 ? '1px solid #eee' : 'none',
                            marginTop: depth === 0 ? '8px' : '0'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1 }}>
                                {allProductIds.length > 0 && (
                                    <input
                                        type="checkbox"
                                        checked={isChecked}
                                        ref={el => {
                                            if (el) el.indeterminate = isIndeterminate;
                                        }}
                                        onChange={() => onToggleCategoryProducts(categoryId)}
                                        disabled={savingId !== null}
                                        style={{ accentColor: '#3182ce' }}
                                    />
                                )}
                                <span style={{ 
                                    fontWeight: depth === 0 ? '700' : depth === 1 ? '600' : '500',
                                    color: depth === 0 ? '#111' : depth === 1 ? '#444' : '#666',
                                    fontSize: depth === 0 ? '14px' : '13px'
                                }}>
                                    {depth > 0 ? '└─ ' : ''}{node.label}
                                </span>
                            </div>
                            {isSaving && <span className="spinner-border spinner-border-sm text-primary" style={{ marginLeft: '8px' }} />}
                        </div>
                        
                        {hasProducts && (
                            <div style={{ marginLeft: '18px' }}>
                                {categoryProducts.map((p) => {
                                    const productId = Number(p.id);
                                    const isLinked = selectedIds.has(productId);
                                    const isSavingProd = savingId === `prod-${productId}`;
                                    return (
                                        <div key={p.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '3px 0' }}>
                                            <label className={cx('category-item')} style={{ display: 'flex', alignItems: 'center', margin: 0, cursor: 'pointer', flex: 1 }}>
                                                <input
                                                    type="checkbox"
                                                    checked={isLinked}
                                                    onChange={() => onToggleProduct(productId)}
                                                    disabled={savingId !== null}
                                                    style={{ marginRight: '6px' }}
                                                />
                                                <span className="text-dark" style={{ fontSize: '13px' }}>
                                                    {p.nameProducts}
                                                </span>
                                            </label>
                                            {isSavingProd && <span className="spinner-border spinner-border-sm text-primary" style={{ marginLeft: '8px' }} />}
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {hasChildren && (
                            <ProductCategoryTreeSelect
                                nodes={node.children}
                                productsByCategoryId={productsByCategoryId}
                                selectedIds={selectedIds}
                                onToggleProduct={onToggleProduct}
                                onToggleCategoryProducts={onToggleCategoryProducts}
                                savingId={savingId}
                                depth={depth + 1}
                            />
                        )}
                    </div>
                );
            })}
        </>
    );
}

// =================== MANAGE PROMOTION TARGETS ===================
export function ModalManagePromotionTargets({ show, setShow, promotionId }) {
    const handleClose = () => setShow(false);

    const [allProducts, setAllProducts] = useState([]);
    const [allCategories, setAllCategories] = useState([]);
    
    const [linkedProductIds, setLinkedProductIds] = useState(new Set());
    const [linkedCategoryIds, setLinkedCategoryIds] = useState(new Set());

    const [loading, setLoading] = useState(false);
    const [savingId, setSavingId] = useState(null); // track which target is being added/removed
    const [productSearch, setProductSearch] = useState('');
    const [categorySearch, setCategorySearch] = useState('');
    const [isGlobal, setIsGlobal] = useState(false);
    const [error, setError] = useState('');

    // Fetch lists
    useEffect(() => {
        if (show && promotionId) {
            setError('');
            setLoading(true);
            Promise.all([
                fetchAdminProducts(),
                fetchAdminCategories({}),
                request.get(`/admin/promotions/${promotionId}/products`),
                request.get(`/admin/promotions/${promotionId}/categories`)
            ])
            .then(([products, categories, linkedProds, linkedCats]) => {
                setAllProducts(products || []);
                setAllCategories(buildCategoryOptions(categories || []));
                const prodIds = new Set((linkedProds.data || []).map(p => p.product_id));
                const catIds = new Set((linkedCats.data || []).map(c => c.category_id));
                setLinkedProductIds(prodIds);
                setLinkedCategoryIds(catIds);
                setIsGlobal(prodIds.size === 0 && catIds.size === 0);
            })
            .catch((err) => setError(getApiError(err, 'Lỗi tải dữ liệu áp dụng khuyến mãi')))
            .finally(() => setLoading(false));
        }
    }, [show, promotionId]);

    const handleSetGlobal = async () => {
        try {
            setSavingId('set-global');
            setError('');
            await request.delete(`/admin/promotions/${promotionId}/targets`);
            setLinkedProductIds(new Set());
            setLinkedCategoryIds(new Set());
            setIsGlobal(true);
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi áp dụng toàn cửa hàng'));
        } finally {
            setSavingId(null);
        }
    };

    const handleToggleProduct = async (productId) => {
        const isLinked = linkedProductIds.has(productId);
        const uniqueId = `prod-${productId}`;
        try {
            setSavingId(uniqueId);
            setError('');
            if (isLinked) {
                // remove
                await request.delete(`/admin/promotions/${promotionId}/products/${productId}`);
                setLinkedProductIds((prev) => {
                    const next = new Set(prev);
                    next.delete(productId);
                    return next;
                });
            } else {
                // add
                await request.post(`/admin/promotions/${promotionId}/products`, {
                    product_id: productId,
                    active: true
                });
                setLinkedProductIds((prev) => {
                    const next = new Set(prev);
                    next.add(productId);
                    return next;
                });
            }
        } catch (err) {
            setError(getApiError(err, 'Không thể thay đổi sản phẩm liên kết'));
        } finally {
            setSavingId(null);
        }
    };

    const handleToggleCategory = async (categoryId) => {
        const descendantIds = getDescendantCategoryIds(categoryId, categoryTree);
        const isCurrentlyLinked = linkedCategoryIds.has(categoryId);
        const uniqueId = `cat-${categoryId}`;
        try {
            setSavingId(uniqueId);
            setError('');
            if (isCurrentlyLinked) {
                // remove
                const toRemove = descendantIds.filter(id => linkedCategoryIds.has(id));
                await Promise.all(
                    toRemove.map(id => request.delete(`/admin/promotions/${promotionId}/categories/${id}`))
                );
                setLinkedCategoryIds((prev) => {
                    const next = new Set(prev);
                    toRemove.forEach(id => next.delete(id));
                    return next;
                });
            } else {
                // add
                const toAdd = descendantIds.filter(id => !linkedCategoryIds.has(id));
                await Promise.all(
                    toAdd.map(id => request.post(`/admin/promotions/${promotionId}/categories`, {
                        category_id: id,
                        active: true
                    }))
                );
                setLinkedCategoryIds((prev) => {
                    const next = new Set(prev);
                    toAdd.forEach(id => next.add(id));
                    return next;
                });
            }
        } catch (err) {
            setError(getApiError(err, 'Không thể thay đổi danh mục liên kết'));
        } finally {
            setSavingId(null);
        }
    };

    const handleToggleCategoryProducts = async (categoryId) => {
        const productIds = collectProductsUnderCategory(categoryId, productTree, productsByCategoryId);
        if (productIds.length === 0) return;
        const allLinked = productIds.every(id => linkedProductIds.has(id));
        const uniqueId = `cat-prod-${categoryId}`;
        try {
            setSavingId(uniqueId);
            setError('');
            if (allLinked) {
                // remove
                await Promise.all(
                    productIds.map(id => request.delete(`/admin/promotions/${promotionId}/products/${id}`))
                );
                setLinkedProductIds((prev) => {
                    const next = new Set(prev);
                    productIds.forEach(id => next.delete(id));
                    return next;
                });
            } else {
                // add
                const toAdd = productIds.filter(id => !linkedProductIds.has(id));
                await Promise.all(
                    toAdd.map(id => request.post(`/admin/promotions/${promotionId}/products`, {
                        product_id: id,
                        active: true
                    }))
                );
                setLinkedProductIds((prev) => {
                    const next = new Set(prev);
                    toAdd.forEach(id => next.add(id));
                    return next;
                });
            }
        } catch (err) {
            setError(getApiError(err, 'Không thể thay đổi sản phẩm liên kết'));
        } finally {
            setSavingId(null);
        }
    };

    const handleApplyAllProducts = async () => {
        const toAdd = filteredProducts.filter(p => !linkedProductIds.has(p.id));
        if (toAdd.length === 0) return;
        try {
            setSavingId('all-products');
            setError('');
            await Promise.all(
                toAdd.map(p => request.post(`/admin/promotions/${promotionId}/products`, {
                    product_id: p.id,
                    active: true
                }))
            );
            setLinkedProductIds(prev => {
                const next = new Set(prev);
                toAdd.forEach(p => next.add(p.id));
                return next;
            });
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi áp dụng tất cả sản phẩm'));
        } finally {
            setSavingId(null);
        }
    };

    const handleRemoveAllProducts = async () => {
        const toRemove = filteredProducts.filter(p => linkedProductIds.has(p.id));
        if (toRemove.length === 0) return;
        try {
            setSavingId('all-products');
            setError('');
            await Promise.all(
                toRemove.map(p => request.delete(`/admin/promotions/${promotionId}/products/${p.id}`))
            );
            setLinkedProductIds(prev => {
                const next = new Set(prev);
                toRemove.forEach(p => next.delete(p.id));
                return next;
            });
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi bỏ áp dụng tất cả sản phẩm'));
        } finally {
            setSavingId(null);
        }
    };

    const handleApplyAllCategories = async () => {
        const toAdd = filteredCategories.filter(c => !linkedCategoryIds.has(Number(c.id)));
        if (toAdd.length === 0) return;
        try {
            setSavingId('all-categories');
            setError('');
            await Promise.all(
                toAdd.map(c => request.post(`/admin/promotions/${promotionId}/categories`, {
                    category_id: Number(c.id),
                    active: true
                }))
            );
            setLinkedCategoryIds(prev => {
                const next = new Set(prev);
                toAdd.forEach(c => next.add(Number(c.id)));
                return next;
            });
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi áp dụng tất cả danh mục'));
        } finally {
            setSavingId(null);
        }
    };

    const handleRemoveAllCategories = async () => {
        const toRemove = filteredCategories.filter(c => linkedCategoryIds.has(Number(c.id)));
        if (toRemove.length === 0) return;
        try {
            setSavingId('all-categories');
            setError('');
            await Promise.all(
                toRemove.map(c => request.delete(`/admin/promotions/${promotionId}/categories/${Number(c.id)}`))
            );
            setLinkedCategoryIds(prev => {
                const next = new Set(prev);
                toRemove.forEach(c => next.delete(Number(c.id)));
                return next;
            });
        } catch (err) {
            setError(getApiError(err, 'Lỗi khi bỏ áp dụng tất cả danh mục'));
        } finally {
            setSavingId(null);
        }
    };

    const filteredProducts = allProducts.filter(p => {
        const name = (p.nameProducts || '').toLowerCase();
        const kw = productSearch.toLowerCase();
        return name.includes(kw);
    });

    const filteredCategories = allCategories.filter(cat => {
        const name = (cat.label || '').toLowerCase();
        const kw = categorySearch.toLowerCase();
        return name.includes(kw);
    });

    // Group filtered products by Category ID
    const productsByCategoryId = {};
    const uncategorizedProducts = [];

    filteredProducts.forEach((p) => {
        const catIds = p.category_ids || [];
        let grouped = false;
        catIds.forEach((catId) => {
            const cId = Number(catId);
            const exists = allCategories.some(c => Number(c.id) === cId);
            if (exists) {
                if (!productsByCategoryId[cId]) {
                    productsByCategoryId[cId] = [];
                }
                productsByCategoryId[cId].push(p);
                grouped = true;
            }
        });
        if (!grouped) {
            uncategorizedProducts.push(p);
        }
    });

    // Build category tree structures
    const categoryTree = filterTree(buildCategoryTree(allCategories), categorySearch);
    const productTree = filterTreeForProducts(buildCategoryTree(allCategories), productsByCategoryId);

    return (
        <Modal show={show} onHide={handleClose} size="xl">
            <Modal.Header closeButton>
                <Modal.Title>Cấu Hình Áp Dụng Khuyến Mãi (ID: {promotionId})</Modal.Title>
            </Modal.Header>
            <Modal.Body className={cx('product-edit-body')} style={{ maxHeight: '78vh' }}>
                <div className={cx('product-edit-box-title')}>
                    <h4>Cấu Hình Áp Dụng Khuyến Mãi</h4>
                </div>
                {error && <div className="alert alert-danger">{error}</div>}
                
                {loading ? (
                    <div className="text-center p-5 text-muted">
                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        Đang tải dữ liệu...
                    </div>
                ) : (
                    <>
                        {/* SCOPE SELECTOR */}
                        <div className="mb-4 p-3 rounded" style={{ backgroundColor: '#2d3748', border: '1px solid #4a5568' }}>
                            <h6 className="text-light mb-3" style={{ fontWeight: 600 }}>Phạm vi áp dụng chương trình khuyến mãi:</h6>
                            <div className="d-flex gap-4">
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', color: '#fff', fontSize: '15px' }}>
                                    <input 
                                        type="radio" 
                                        name="applyScope" 
                                        checked={isGlobal} 
                                        onChange={handleSetGlobal}
                                        disabled={savingId !== null}
                                        style={{ accentColor: '#3182ce', width: '18px', height: '18px' }}
                                    />
                                    <strong>Áp dụng cho tất cả sản phẩm (Toàn bộ cửa hàng)</strong>
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', color: '#fff', fontSize: '15px' }}>
                                    <input 
                                        type="radio" 
                                        name="applyScope" 
                                        checked={!isGlobal} 
                                        onChange={() => setIsGlobal(false)}
                                        disabled={savingId !== null}
                                        style={{ accentColor: '#3182ce', width: '18px', height: '18px' }}
                                    />
                                    <strong>Chỉ áp dụng cho các danh mục hoặc sản phẩm được chọn bên dưới</strong>
                                </label>
                            </div>
                        </div>

                        <div className="row" style={{ opacity: isGlobal ? 0.45 : 1, pointerEvents: isGlobal ? 'none' : 'auto', transition: 'all 0.2s ease' }}>
                            {/* CATEGORIES COLUMN */}
                            <div className="col-md-5 border-end">
                                <h5 className="mb-3 text-dark d-flex align-items-center justify-content-between">
                                    <span>Áp dụng cho Danh mục</span>
                                    {isGlobal && <span className="badge bg-secondary font-monospace" style={{ fontSize: '11px' }}>TỰ ĐỘNG ÁP DỤNG</span>}
                                </h5>
                                <p className="text-muted small">Nếu chọn danh mục, khuyến mãi sẽ áp dụng cho tất cả sản phẩm thuộc danh mục đó.</p>
                                
                                <div className="mb-3 d-flex gap-2 align-items-center">
                                    <input
                                        type="text"
                                        className="form-control"
                                        placeholder="Tìm kiếm danh mục..."
                                        value={categorySearch}
                                        onChange={(e) => setCategorySearch(e.target.value)}
                                        style={{ flex: 1 }}
                                    />
                                    <button
                                        type="button"
                                        className="btn btn-sm btn-outline-success text-nowrap"
                                        onClick={handleApplyAllCategories}
                                        disabled={savingId !== null || filteredCategories.length === 0}
                                    >
                                        {savingId === 'all-categories' ? 'Đang xử lý...' : 'Áp dụng tất cả'}
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-sm btn-outline-danger text-nowrap"
                                        onClick={handleRemoveAllCategories}
                                        disabled={savingId !== null || filteredCategories.length === 0}
                                    >
                                        {savingId === 'all-categories' ? 'Đang xử lý...' : 'Bỏ áp dụng tất cả'}
                                    </button>
                                </div>

                                <div className={cx('category-multiselect')} style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                    {categoryTree.length === 0 ? (
                                        <div className="text-muted p-2">Không tìm thấy danh mục phù hợp</div>
                                    ) : (
                                        <CategoryTreeSelect
                                            nodes={categoryTree}
                                            selectedIds={linkedCategoryIds}
                                            onToggle={handleToggleCategory}
                                            savingId={savingId}
                                        />
                                    )}
                                </div>
                            </div>

                            {/* PRODUCTS COLUMN */}
                            <div className="col-md-7">
                                <h5 className="mb-3 text-dark d-flex align-items-center justify-content-between">
                                    <span>Áp dụng cho Sản phẩm cụ thể</span>
                                    {isGlobal && <span className="badge bg-secondary font-monospace" style={{ fontSize: '11px' }}>TỰ ĐỘNG ÁP DỤNG</span>}
                                </h5>
                                <div className="mb-3 d-flex gap-2 align-items-center">
                                    <input
                                        type="text"
                                        className="form-control"
                                        placeholder="Tìm kiếm sản phẩm theo tên..."
                                        value={productSearch}
                                        onChange={(e) => setProductSearch(e.target.value)}
                                        style={{ flex: 1 }}
                                    />
                                    <button
                                        type="button"
                                        className="btn btn-sm btn-outline-success text-nowrap"
                                        onClick={handleApplyAllProducts}
                                        disabled={savingId !== null || filteredProducts.length === 0}
                                    >
                                        {savingId === 'all-products' ? 'Đang xử lý...' : 'Áp dụng tất cả'}
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-sm btn-outline-danger text-nowrap"
                                        onClick={handleRemoveAllProducts}
                                        disabled={savingId !== null || filteredProducts.length === 0}
                                    >
                                        {savingId === 'all-products' ? 'Đang xử lý...' : 'Bỏ áp dụng tất cả'}
                                    </button>
                                </div>
                                <div className={cx('category-multiselect')} style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                    {productTree.length === 0 && uncategorizedProducts.length === 0 ? (
                                        <div className="text-muted p-2">Không tìm thấy sản phẩm phù hợp</div>
                                    ) : (
                                        <>
                                            <ProductCategoryTreeSelect
                                                nodes={productTree}
                                                productsByCategoryId={productsByCategoryId}
                                                selectedIds={linkedProductIds}
                                                onToggleProduct={handleToggleProduct}
                                                onToggleCategoryProducts={handleToggleCategoryProducts}
                                                savingId={savingId}
                                            />
                                            {uncategorizedProducts.length > 0 && (
                                                <div style={{ marginTop: '12px' }}>
                                                    <div style={{ 
                                                        fontWeight: '700', 
                                                        color: '#111', 
                                                        fontSize: '14px', 
                                                        padding: '4px 0', 
                                                        borderBottom: '1px solid #eee' 
                                                    }}>
                                                        Sản phẩm khác (Không có danh mục)
                                                    </div>
                                                    <div style={{ marginLeft: '18px', marginTop: '6px' }}>
                                                        {uncategorizedProducts.map((p) => {
                                                            const productId = Number(p.id);
                                                            const isLinked = linkedProductIds.has(productId);
                                                            const isSaving = savingId === `prod-${productId}`;
                                                            return (
                                                                <div key={p.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '3px 0' }}>
                                                                    <label className={cx('category-item')} style={{ display: 'flex', alignItems: 'center', margin: 0, cursor: 'pointer', flex: 1 }}>
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={isLinked}
                                                                            onChange={() => handleToggleProduct(productId)}
                                                                            disabled={savingId !== null}
                                                                            style={{ marginRight: '6px' }}
                                                                        />
                                                                        <span className="text-dark" style={{ fontSize: '13px' }}>
                                                                            {p.nameProducts}
                                                                        </span>
                                                                    </label>
                                                                    {isSaving && <span className="spinner-border spinner-border-sm text-primary" style={{ marginLeft: '8px' }} />}
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </Modal.Body>
            <Modal.Footer>
                <span className="text-muted me-auto small">Lưu ý: Các thay đổi checkbox sẽ được cập nhật trực tiếp lên hệ thống.</span>
                <Button variant="secondary" onClick={handleClose}>Đóng</Button>
            </Modal.Footer>
        </Modal>
    );
}
