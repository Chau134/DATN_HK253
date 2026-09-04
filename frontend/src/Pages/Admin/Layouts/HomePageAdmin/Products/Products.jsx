import React, { useEffect, useState, useRef } from 'react';
import classNames from 'classnames/bind';

import { fetchAdminCategories } from '../../../../../api/adminCatalogApi';
import { ModalAddProduct, ModalDeleteProduct, ModalEditProduct } from '../../../Modal/Modal';
import styles from './Products.module.scss';

const cx = classNames.bind(styles);
const tableTextStyle = { color: '#fff' };

function formatPrice(value) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        maximumFractionDigits: 0,
    }).format(Number(value || 0));
}

/* ── build tree from flat list ── */
function buildCategoryTree(list) {
    const map = {};
    list.forEach((cat) => {
        map[String(cat.id)] = { ...cat, children: [] };
    });
    const roots = [];
    list.forEach((cat) => {
        const node = map[String(cat.id)];
        const pid = cat.parent_id ? String(cat.parent_id) : null;
        if (pid && map[pid]) map[pid].children.push(node);
        else roots.push(node);
    });
    return roots;
}

/* Sum product counts up the tree (includes descendants) */
function sumCounts(node, countMap) {
    const own = countMap.get(String(node.id)) || 0;
    const childSum = (node.children || []).reduce((s, c) => s + sumCounts(c, countMap), 0);
    return own + childSum;
}

/* ── Recursive tree node ── */
function CategoryTreeNode({ node, countMap, selectedId, onSelect }) {
    const [open, setOpen] = useState(false);
    const hasChildren = node.children && node.children.length > 0;
    const label = node.label || node.name_vi || node.name || `Danh mục ${node.id}`;
    const nodeId = String(node.id);
    const total = sumCounts(node, countMap);
    const isActive = selectedId === nodeId;

    return (
        <div className={cx('tree-node')}>
            <div className={cx('tree-row', { 'tree-row--active': isActive })}>
                {hasChildren ? (
                    <button
                        className={cx('tree-toggle')}
                        onClick={(e) => { e.stopPropagation(); setOpen(o => !o); }}
                    >
                        <span className={cx('chevron', { 'chevron--open': open })}>›</span>
                    </button>
                ) : (
                    <span className={cx('tree-leaf-dot')} />
                )}
                <button
                    className={cx('tree-label')}
                    onClick={() => onSelect(isActive ? '' : nodeId)}
                    title={label}
                >
                    {label}
                </button>
                {total > 0 && (
                    <span className={cx('tree-count')}>{total}</span>
                )}
            </div>
            {hasChildren && open && (
                <div className={cx('tree-children')}>
                    {node.children.map(child => (
                        <CategoryTreeNode
                            key={child.id}
                            node={child}
                            countMap={countMap}
                            selectedId={selectedId}
                            onSelect={onSelect}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

/* ── Main Products component ── */
function Products({
    dataProducts,
    show,
    setShow,
    handleShowModalAddProduct,
    showModalDelete,
    setShowModalDelete,
    handleShowModalDeleteProduct,
    idProduct,
    handleShowModalEditProduct,
    showModalEdit,
    setShowModalEdit,
    setValueType,
    valueType,
    onProductChanged,
}) {
    const [categories, setCategories] = useState([]);
    const [categoryTree, setCategoryTree] = useState([]);
    const [loading, setLoading] = useState(false);
    const [dropOpen, setDropOpen] = useState(false);
    const dropRef = useRef(null);

    useEffect(() => {
        setLoading(true);
        fetchAdminCategories({})
            .then((list) => {
                setCategories(list);
                setCategoryTree(buildCategoryTree(list));
            })
            .catch((err) => console.error('Lỗi khi lấy danh mục:', err))
            .finally(() => setLoading(false));
    }, []);

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e) => {
            if (dropRef.current && !dropRef.current.contains(e.target)) setDropOpen(false);
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const getCategoryLabel = (categoryId) => {
        const cat = categories.find(c => String(c.id) === String(categoryId));
        return cat ? (cat.label || cat.name_vi || cat.name) : (categoryId || 'Chưa có');
    };

    const products = Array.isArray(dataProducts) ? dataProducts : [];

    // Build countMap: how many products per category id
    const countMap = products.reduce((m, item) => {
        const id = String(item.checkProducts || '');
        if (id) m.set(id, (m.get(id) || 0) + 1);
        return m;
    }, new Map());

    const filteredProducts = products.filter(
        item => valueType === '' || String(item.checkProducts) === valueType
    );

    const selectedLabel = valueType
        ? getCategoryLabel(valueType)
        : 'Lọc Theo Danh Mục';

    const handleSelect = (id) => {
        setValueType(id);
        setDropOpen(false);
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('header-product')}>
                <h1>Sản Phẩm</h1>
                <button onClick={handleShowModalAddProduct} type="button" className="btn btn-primary">
                    Thêm Sản Phẩm
                </button>
            </div>

            {/* Category tree filter */}
            <div className={cx('filter-bar')}>
                <div className={cx('cat-dropdown')} ref={dropRef}>
                    <button
                        className={cx('cat-trigger', { 'cat-trigger--active': !!valueType })}
                        onClick={() => setDropOpen(o => !o)}
                        type="button"
                        disabled={loading}
                        style={{
                            background: '#ffffff',
                            color: '#111111',
                            border: valueType ? '2px solid #0d6efd' : '1px solid #ccc',
                            borderRadius: '8px',
                            height: '48px',
                            padding: '0 20px',
                            fontSize: '15px',
                            fontWeight: 600,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '8px',
                            width: '100%',
                            maxWidth: '480px',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            boxShadow: 'none',
                            whiteSpace: 'nowrap',
                        }}
                    >
                        <span className={cx('cat-trigger-icon')}>☰</span>
                        <span className={cx('cat-trigger-label')}>{selectedLabel}</span>
                        <span className={cx('cat-trigger-arrow', { 'cat-trigger-arrow--open': dropOpen })}>▾</span>
                    </button>

                    {dropOpen && (
                        <div className={cx('cat-panel')}>
                            <div className={cx('cat-panel-header')}>
                                <span>Danh mục sản phẩm</span>
                                {valueType && (
                                    <button className={cx('cat-clear')} onClick={() => handleSelect('')}>
                                        ✕ Bỏ chọn
                                    </button>
                                )}
                            </div>
                            <div className={cx('cat-scroll')}>
                                {categoryTree.length === 0 ? (
                                    <div className={cx('cat-empty')}>Đang tải...</div>
                                ) : (
                                    categoryTree.map(node => (
                                        <CategoryTreeNode
                                            key={node.id}
                                            node={node}
                                            countMap={countMap}
                                            selectedId={valueType}
                                            onSelect={handleSelect}
                                        />
                                    ))
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <span className={cx('filter-count')}>
                    {filteredProducts.length} / {products.length} sản phẩm
                </span>
            </div>

            <table className={cx('product-table')}>
                <thead>
                    <tr>
                        <th style={tableTextStyle}>ID</th>
                        <th style={tableTextStyle}>Tên Sản Phẩm</th>
                        <th style={tableTextStyle}>Ảnh Sản Phẩm</th>
                        <th style={tableTextStyle}>Giá Bán</th>
                        <th style={tableTextStyle}>Giá Nhập</th>
                        <th style={tableTextStyle}>VAT</th>
                        <th style={tableTextStyle}>Danh mục</th>
                        <th style={tableTextStyle}>Số lượng</th>
                        <th style={tableTextStyle}>Hành Động</th>
                    </tr>
                </thead>
                <tbody>
                    {filteredProducts.map((item) => (
                        <tr key={item._id}>
                            <th style={tableTextStyle}>{item.id}</th>
                            <td style={tableTextStyle}>{item.nameProducts}</td>
                            <td style={tableTextStyle}>
                                {item.img ? (
                                    <img
                                        style={{ width: '120px', height: '100px', objectFit: 'cover' }}
                                        src={item.img}
                                        alt={item.nameProducts || 'Sản phẩm'}
                                    />
                                ) : (
                                    <span>Chưa có ảnh</span>
                                )}
                            </td>
                            <td style={tableTextStyle}>{formatPrice(item.sellingPrice)}</td>
                            <td style={tableTextStyle}>{formatPrice(item.importPrice)}</td>
                            <td style={tableTextStyle}>{item.vat != null ? `${item.vat}%` : '0%'}</td>
                            <td style={tableTextStyle}>{getCategoryLabel(item.checkProducts)}</td>
                            <td style={tableTextStyle}>{item.quantityPro || 0}</td>
                            <td className={cx('actions')} style={tableTextStyle}>
                                <button
                                    onClick={() => handleShowModalEditProduct(item.id)}
                                    type="button"
                                    className="btn btn-warning"
                                >
                                    Sửa Sản Phẩm
                                </button>
                                <button
                                    onClick={() => handleShowModalDeleteProduct(item.id)}
                                    type="button"
                                    className="btn btn-danger"
                                >
                                    Xóa Sản Phẩm
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <ModalAddProduct show={show} setShow={setShow} onProductChanged={onProductChanged} />
            <ModalDeleteProduct
                showModalDelete={showModalDelete}
                setShowModalDelete={setShowModalDelete}
                idProduct={idProduct}
                onProductChanged={onProductChanged}
            />
            <ModalEditProduct
                showModalEdit={showModalEdit}
                setShowModalEdit={setShowModalEdit}
                idProduct={idProduct}
                onProductChanged={onProductChanged}
            />
        </div>
    );
}

export default Products;
