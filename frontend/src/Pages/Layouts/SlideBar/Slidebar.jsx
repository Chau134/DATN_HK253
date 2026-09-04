import React, { useEffect, useState, useRef } from 'react';
import classNames from 'classnames/bind';
import styles from './Slidebar.module.scss';
import { fetchCatalogCategories } from '../../../api/catalogApi';

const cx = classNames.bind(styles);

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


function getCategoryLabel(cat) {
    return cat.name_vi || cat.name || `Danh mục ${cat.id}`;
}

function collectDescendantIds(node) {
    const ids = [String(node.id)];
    (node.children || []).forEach((c) => ids.push(...collectDescendantIds(c)));
    return ids;
}

function CategoryTreeNode({ node, selectedId, onSelect, depth }) {
    const [open, setOpen] = useState(false);
    const hasChildren = node.children && node.children.length > 0;
    const label = getCategoryLabel(node);
    const nodeId = String(node.id);

    // Highlight if this node or any descendant is selected
    const isActive = selectedId === nodeId;
    const descendantIds = collectDescendantIds(node);
    const hasActiveChild = descendantIds.includes(selectedId) && !isActive;

    return (
        <div className={cx('tree-node')}>
            <div
                className={cx('tree-row', {
                    'tree-row--active': isActive,
                    'tree-row--child-active': hasActiveChild,
                })}
                style={{ paddingLeft: `${depth * 14 + 10}px` }}
            >
                {hasChildren && (
                    <button
                        className={cx('tree-toggle')}
                        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
                        aria-label={open ? 'Thu gọn' : 'Mở rộng'}
                    >
                        <span className={cx('chevron', { 'chevron--open': open })}>›</span>
                    </button>
                )}
                {!hasChildren && <span className={cx('tree-leaf-dot')} />}
                <button
                    className={cx('tree-label')}
                    onClick={() => onSelect(isActive ? '' : nodeId)}
                    title={label}
                >
                    {label}
                </button>
            </div>
            {hasChildren && open && (
                <div className={cx('tree-children')}>
                    {node.children.map((child) => (
                        <CategoryTreeNode
                            key={child.id}
                            node={child}
                            selectedId={selectedId}
                            onSelect={onSelect}
                            depth={depth + 1}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

function SlideBar({ setCategoryId, setCheckPrice, categoryId }) {
    const [tree, setTree] = useState([]);
    const [allCategories, setAllCategories] = useState([]);
    const [catOpen, setCatOpen] = useState(false);
    const catRef = useRef(null);

    useEffect(() => {
        fetchCatalogCategories()
            .then((list) => {
                setAllCategories(list);
                setTree(buildCategoryTree(list));
            })
            .catch(() => { setAllCategories([]); setTree([]); });
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (catRef.current && !catRef.current.contains(e.target)) {
                setCatOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const selectedLabel = categoryId
        ? (() => {
              const found = allCategories.find((c) => String(c.id) === String(categoryId));
              return found ? getCategoryLabel(found) : 'Danh mục';
          })()
        : 'Lọc Theo Danh Mục';

    const handleSelect = (id) => {
        setCategoryId(id);
        setCatOpen(false);
    };

    return (
        <div className={cx('wrapper')}>
            {/* Category tree dropdown */}
            <div className={cx('dropdown-wrap')} ref={catRef}>
                <button
                    className={cx('dropdown-trigger', { 'dropdown-trigger--active': !!categoryId })}
                    onClick={() => setCatOpen((o) => !o)}
                    type="button"
                >
                    <span className={cx('trigger-icon')}>☰</span>
                    <span className={cx('trigger-label')}>{selectedLabel}</span>
                    <span className={cx('trigger-arrow', { 'trigger-arrow--open': catOpen })}>▾</span>
                </button>

                {catOpen && (
                    <div className={cx('dropdown-panel')}>
                        <div className={cx('panel-header')}>
                            <span>Danh mục sản phẩm</span>
                            {categoryId && (
                                <button
                                    className={cx('clear-btn')}
                                    onClick={() => handleSelect('')}
                                >
                                    ✕ Bỏ chọn
                                </button>
                            )}
                        </div>
                        <div className={cx('tree-scroll')}>
                            {tree.length === 0 ? (
                                <div className={cx('tree-empty')}>Đang tải...</div>
                            ) : (
                                tree.map((node) => (
                                    <CategoryTreeNode
                                        key={node.id}
                                        node={node}
                                        selectedId={String(categoryId || '')}
                                        onSelect={handleSelect}
                                        depth={0}
                                    />
                                ))
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Price filter */}
            <div className={cx('select-option')}>
                <select
                    className={cx('price-select')}
                    aria-label="Select price"
                    onChange={(e) => setCheckPrice(e.target.value)}
                >
                    <option value="">Lọc Theo Giá</option>
                    <option value="1">Giá từ cao đến thấp</option>
                    <option value="2">Giá từ thấp đến cao</option>
                </select>
            </div>
        </div>
    );
}

export default SlideBar;
