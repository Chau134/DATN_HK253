import React, { useContext, useEffect, useState } from 'react';
import classNames from 'classnames/bind';

import request, { getApiError } from '../../../config/Connect';
import { fetchAdminCategories } from '../../../api/adminCatalogApi';
import styles from './Modal.module.scss';

const cx = classNames.bind(styles);
const ModalContext = React.createContext({ onHide: () => {} });

const categoryNoiseWords = ['khuyen mai', 'giam gia', 'thanh ly', 'sale', 'ban hang', 'promotion', 'discount', 'clearance'];

const defaultGenders = ['Men', 'Women', 'Boys', 'Girls', 'Unisex'];
const defaultGendersVi = ['Nam', 'Nữ', 'Bé trai', 'Bé gái', 'Unisex'];
const defaultSeasons = ['Summer', 'Fall', 'Winter', 'Spring', 'All Season'];
const defaultSeasonsVi = ['Hè', 'Thu', 'Đông', 'Xuân', 'Cả năm'];

function capitalizeFirstLetter(val) {
    if (!val) return '';
    const s = String(val).trim();
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1);
}

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

function getDescendantIds(catId, list) {
    let ids = [String(catId)];
    const children = list.filter(c => String(c.parent_id || c.parentId) === String(catId));
    children.forEach(child => {
        ids = ids.concat(getDescendantIds(child.id || child.value, list));
    });
    return Array.from(new Set(ids));
}

function CategoryTreeSelect({ nodes, selectedIds, onToggle, onDeleteLocal, depth = 0 }) {
    if (!Array.isArray(nodes) || nodes.length === 0) return null;
    
    return (
        <>
            {nodes.map((node) => {
                const collectDescendantValues = (n) => {
                    let vals = [String(n.value || n.id)];
                    if (n.children) {
                        n.children.forEach(child => {
                            vals = vals.concat(collectDescendantValues(child));
                        });
                    }
                    return vals;
                };
                const allDescendantVals = collectDescendantValues(node);
                const isChecked = allDescendantVals.every(val => selectedIds.includes(val));
                const isIndeterminate = !isChecked && allDescendantVals.some(val => selectedIds.includes(val));
                const isNew = node.isNew === true;
                return (
                    <div key={node.id} style={{ marginLeft: `${depth * 18}px` }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '2px 0' }}>
                            <label className={cx('category-item')} style={{ display: 'flex', alignItems: 'center', margin: 0, cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    value={node.value}
                                    checked={isChecked}
                                    ref={el => {
                                        if (el) el.indeterminate = isIndeterminate;
                                    }}
                                    onChange={() => onToggle(node.value)}
                                    style={{ marginRight: '6px' }}
                                />
                                <span style={{ 
                                    fontWeight: depth === 0 ? '700' : depth === 1 ? '600' : '400',
                                    color: isNew ? '#0066cc' : (depth === 0 ? '#111' : depth === 1 ? '#333' : '#555'),
                                    fontSize: depth === 0 ? '14px' : '13px',
                                    fontStyle: isNew ? 'italic' : 'normal'
                                }}>
                                    {depth > 0 ? '└─ ' : ''}{node.label} {isNew ? '(Mới thêm)' : ''}
                                </span>
                            </label>
                            {isNew && onDeleteLocal && (
                                <button
                                    type="button"
                                    onClick={() => onDeleteLocal(node.id)}
                                    style={{
                                        border: 'none',
                                        background: 'transparent',
                                        color: '#e74c3c',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        padding: '0 4px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        lineHeight: 1
                                    }}
                                    title="Xóa danh mục tạm này"
                                >
                                    ✕
                                </button>
                            )}
                        </div>
                        {node.children && node.children.length > 0 && (
                            <CategoryTreeSelect 
                                nodes={node.children} 
                                selectedIds={selectedIds} 
                                onToggle={onToggle} 
                                onDeleteLocal={onDeleteLocal}
                                depth={depth + 1} 
                            />
                        )}
                    </div>
                );
            })}
        </>
    );
}

function findCategoryByLabel(categories, label) {
    const key = normalizeCategoryOptionLabel(label);
    if (!key) return null;

    return categories.find((category) => {
        const candidates = [getCategoryLabel(category), category?.name_vi, category?.name].filter(Boolean);
        return candidates.some((candidate) => normalizeCategoryOptionLabel(candidate) === key);
    }) || null;
}

function getCategoryPath(category, list) {
    const path = [];
    let current = category;
    const visited = new Set();
    while (current && !visited.has(current.id)) {
        visited.add(current.id);
        path.unshift(current.label || current.name_vi || current.name || `Danh mục ${current.id}`);
        const parentId = current.parent_id || current.parentId;
        current = parentId ? list.find(c => String(c.id) === String(parentId)) : null;
    }
    return path.join(' -> ');
}

async function saveLocalNewCategories(localNewCategories) {
    const tempToRealIdMap = {};
    const queue = [...localNewCategories];

    while (queue.length > 0) {
        const readyIndex = queue.findIndex(cat => {
            const pid = cat.parent_id;
            if (!pid) return true;
            if (!String(pid).startsWith('temp-')) return true;
            return tempToRealIdMap[pid] !== undefined;
        });

        if (readyIndex === -1) {
            throw new Error('Xung đột cây hoặc vòng lặp phụ thuộc danh mục');
        }

        const cat = queue.splice(readyIndex, 1)[0];
        
        let parentId = cat.parent_id;
        if (parentId && String(parentId).startsWith('temp-')) {
            parentId = tempToRealIdMap[parentId];
        }

        const categoryName = (cat.name || '').trim();
        const categoryNameVi = (cat.name_vi || cat.label || '').trim();

        if (!categoryName || !categoryNameVi) {
            throw new Error('Vui long nhap du ten danh muc tieng Anh va tieng Viet');
        }

        const payload = {
            level: parentId ? 'sub' : 'master',
            name: categoryName,
            name_vi: categoryNameVi,
            parent_id: parentId ? Number(parentId) : null,
            active: true
        };

        const res = await request.post('/admin/catalog/categories', payload);
        const savedCat = res.data;
        tempToRealIdMap[cat.id] = String(savedCat.id);
    }

    return tempToRealIdMap;
}

function categoryLabelById(categories, id) {
    const category = categories.find((item) => String(item?.value ?? item?.id) === String(id));
    return category ? getCategoryLabel(category) : `Danh mục ${id}`;
}

function appendCategoryId(ids, id) {
    const nextId = String(id);
    return ids.includes(nextId) ? ids : [...ids, nextId];
}

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
// =================== Thêm Sản Phẩm ===================
export function ModalAddProduct({ show, setShow, onProductChanged }) {
    const [form, setForm] = useState(emptyProductForm);
    const [priceForm, setPriceForm] = useState({ sellingPrice: '', importPrice: '', vat: '0' });
    const [existingData, setExistingData] = useState({
        brands: [],
        ageGroups: [],
        ageGroupsVi: [],
        usages: [],
        usagesVi: [],
        materials: [],
        materialsVi: [],
        fits: [],
        fitsVi: [],
        optionNames: [],
        optionValues: [],
        unifiedSizes: [],
        genders: [],
        gendersVi: [],
        seasons: [],
        seasonsVi: []
    });

    useEffect(() => {
        if (show) {
            request.get('/admin/catalog/products')
                .then((res) => {
                    const products = res.data || [];
                    const brands = new Set();
                    const ageGroups = new Set();
                    const ageGroupsVi = new Set();
                    const usages = new Set();
                    const usagesVi = new Set();
                    const materials = new Set();
                    const materialsVi = new Set();
                    const fits = new Set();
                    const fitsVi = new Set();
                    const optionNames = new Set();
                    const optionValues = new Set();
                    const unifiedSizes = new Set();
                    const gendersSet = new Set();
                    const gendersViSet = new Set();
                    const seasonsSet = new Set();
                    const seasonsViSet = new Set();

                    products.forEach((p) => {
                        if (p.brand) brands.add(String(p.brand).trim());
                        if (p.age_group) ageGroups.add(String(p.age_group).trim());
                        if (p.age_group_vi) ageGroupsVi.add(capitalizeFirstLetter(p.age_group_vi));
                        if (p.usage) usages.add(String(p.usage).trim());
                        if (p.usage_vi) usagesVi.add(capitalizeFirstLetter(p.usage_vi));
                        if (p.material) materials.add(String(p.material).trim());
                        if (p.material_vi) materialsVi.add(capitalizeFirstLetter(p.material_vi));
                        if (p.fit) fits.add(String(p.fit).trim());
                        if (p.fit_vi) fitsVi.add(capitalizeFirstLetter(p.fit_vi));
                        if (p.gender) gendersSet.add(String(p.gender).trim());
                        if (p.gender_vi) gendersViSet.add(capitalizeFirstLetter(p.gender_vi));
                        if (p.season) seasonsSet.add(String(p.season).trim());
                        if (p.season_vi) seasonsViSet.add(capitalizeFirstLetter(p.season_vi));

                        if (Array.isArray(p.variants)) {
                            p.variants.forEach((v) => {
                                if (v.option_name) optionNames.add(String(v.option_name).trim());
                                if (v.option_value) optionValues.add(String(v.option_value).trim());
                                if (v.unified_size) unifiedSizes.add(String(v.unified_size).trim());
                            });
                        }
                    });

                    setExistingData({
                        brands: Array.from(brands),
                        ageGroups: Array.from(ageGroups),
                        ageGroupsVi: Array.from(ageGroupsVi),
                        usages: Array.from(usages),
                        usagesVi: Array.from(usagesVi),
                        materials: Array.from(materials),
                        materialsVi: Array.from(materialsVi),
                        fits: Array.from(fits),
                        fitsVi: Array.from(fitsVi),
                        optionNames: Array.from(optionNames),
                        optionValues: Array.from(optionValues),
                        unifiedSizes: Array.from(unifiedSizes),
                        genders: Array.from(new Set([...defaultGenders, ...gendersSet])),
                        gendersVi: Array.from(new Set([...defaultGendersVi, ...gendersViSet])),
                        seasons: Array.from(new Set([...defaultSeasons, ...seasonsSet])),
                        seasonsVi: Array.from(new Set([...defaultSeasonsVi, ...seasonsViSet])),
                    });
                })
                .catch((err) => console.error('Error fetching existing products data:', err));
        }
    }, [show]);

    const [variantForms, setVariantForms] = useState([newVariantForm()]);
    const [imageForms, setImageForms] = useState([]);
    const [attributeForms, setAttributeForms] = useState([]);
    const [selectedCategoryIds, setSelectedCategoryIds] = useState([]);
    const [mainImageFile, setMainImageFile] = useState(null);
    const [newCategoryName, setNewCategoryName] = useState('');
    const [newCategoryNameEn, setNewCategoryNameEn] = useState('');
    const [newCategoryParentId, setNewCategoryParentId] = useState('');
    const [localNewCategories, setLocalNewCategories] = useState([]);
    const [creatingCategory, setCreatingCategory] = useState(false);
    const [saving, setSaving] = useState(false);
    const [formError, setFormError] = useState('');
    const [categories, setCategories] = useState([]);

    useEffect(() => {
        if (show) {
            fetchAdminCategories()
                .then((list) => setCategories(buildCategoryOptions(list)))
                .catch(() => setCategories([]));
        }
    }, [show]);

    const updateForm = (field, value) => setForm((current) => ({ ...current, [field]: value }));
    const updatePriceForm = (field, value) => setPriceForm((current) => ({ ...current, [field]: value }));
    const updateVariantForm = (index, field, value) => {
        setVariantForms((current) =>
            current.map((variant, variantIndex) => (variantIndex === index ? { ...variant, [field]: value } : variant)),
        );
    };
    const updateImageForm = (index, field, value) => {
        setImageForms((current) =>
            current.map((image, imageIndex) => (imageIndex === index ? { ...image, [field]: value } : image)),
        );
    };
    const updateAttributeForm = (index, field, value) => {
        setAttributeForms((current) =>
            current.map((attribute, attributeIndex) =>
                attributeIndex === index ? { ...attribute, [field]: value } : attribute,
            ),
        );
    };
    const addImageForm = () => setImageForms((current) => [...current, { imageType: 'detail', imageUrl: '', sortOrder: current.length, file: null }]);
    const removeImageForm = (index) => setImageForms((current) => current.filter((_, imageIndex) => imageIndex !== index));
    const addVariantForm = () => setVariantForms((current) => [...current, newVariantForm()]);
    const removeVariantForm = (index) => setVariantForms((current) => (current.length > 1 ? current.filter((_, variantIndex) => variantIndex !== index) : current));
    const addAttributeForm = () => setAttributeForms((current) => [...current, { attrKey: '', attrValue: '', attrValueVi: '' }]);
    const removeAttributeForm = (index) => setAttributeForms((current) => current.filter((_, attributeIndex) => attributeIndex !== index));
    const toggleCategory = (id) => {
        const s = String(id);
        const descendants = getDescendantIds(s, categories.concat(localNewCategories));
        const allSelected = descendants.every((descId) => selectedCategoryIds.includes(descId));
        setSelectedCategoryIds((cur) => {
            if (allSelected) {
                return cur.filter((x) => !descendants.includes(x));
            } else {
                const next = [...cur];
                descendants.forEach((descId) => {
                    if (!next.includes(descId)) {
                        next.push(descId);
                    }
                });
                return next;
            }
        });
    };

    


    

    

    const productPayload = (mainImage = form.mainImage, categoryIds = selectedCategoryIds) => ({
        external_id: numberOrNull(form.externalId),
        article_number: form.articleNumber,
        title: form.title || form.titleVi || 'San pham',
        title_vi: form.titleVi || form.title,
        brand: form.brand,
        variant_name: form.variantName,
        variant_name_vi: form.variantNameVi,
        age_group: form.ageGroup,
        age_group_vi: form.ageGroupVi,
        gender: form.gender,
        gender_vi: form.genderVi,
        base_colour: form.baseColour,
        base_colour_vi: form.baseColourVi,
        colour1: form.colour1,
        colour1_vi: form.colour1Vi,
        colour2: form.colour2,
        colour2_vi: form.colour2Vi,
        season: form.season,
        season_vi: form.seasonVi,
        year: numberOrNull(form.year),
        usage: form.usage,
        usage_vi: form.usageVi,
        material: form.material,
        material_vi: form.materialVi,
        fit: form.fit,
        fit_vi: form.fitVi,
        main_image: mainImage,
        description: form.description,
        description_vi: form.descriptionVi,
        catalog_add_date: toInstantValue(form.catalogAddDate),
        category_ids: categoryIds.map(Number),
    });

    const uploadImageFile = async (productId, file) => {
        if (!file) return '';
        const formData = new FormData();
        formData.append('file', file);
        const response = await request.post(`/admin/catalog/products/${productId}/images/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data?.url || '';
    };

    const resetAddForm = () => {
        setForm(emptyProductForm);
        setPriceForm({ sellingPrice: '', importPrice: '', vat: '0' });
        setVariantForms([newVariantForm()]);
        setImageForms([]);
        setAttributeForms([]);
        setSelectedCategoryIds([]);
        setMainImageFile(null);
        setNewCategoryName('');
        setNewCategoryNameEn('');
        setNewCategoryParentId('');
        setLocalNewCategories([]);
    };

    const handleClose = () => {
        resetAddForm();
        setShow(false);
    };

    const handleAddProduct = async () => {
        try {
            setSaving(true);
            setFormError('');

            let tempToRealMap = {};
            if (localNewCategories.length > 0) {
                tempToRealMap = await saveLocalNewCategories(localNewCategories);
            }

            const finalCategoryIds = selectedCategoryIds.map((id) => {
                if (String(id).startsWith('temp-')) {
                    return Number(tempToRealMap[id]);
                }
                return Number(id);
            });

            const productRes = await request.post('/admin/catalog/products', productPayload(form.mainImage, finalCategoryIds));
            const productId = productRes.data.id;

            const uploadedMainImage = await uploadImageFile(productId, mainImageFile);
            if (uploadedMainImage) {
                await request.put(`/admin/catalog/products/${productId}`, productPayload(uploadedMainImage, finalCategoryIds));
            }

            if (Number(priceForm.sellingPrice) > 0) {
                await request.post(`/admin/catalog/products/${productId}/prices`, {
                    selling_price: Number(priceForm.sellingPrice),
                    import_price: numberOrNull(priceForm.importPrice),
                    vat: numberOrNull(priceForm.vat),
                });
            }

            for (const [index, variant] of variantForms.entries()) {
                if (index > 0 && isVariantFormBlank(variant)) continue;
                await request.post(`/admin/catalog/products/${productId}/variants`, variantPayload(variant, form));
            }

            for (const image of imageForms) {
                const uploadedUrl = await uploadImageFile(productId, image.file);
                const imageUrl = uploadedUrl || image.imageUrl?.trim();
                if (!imageUrl) continue;
                await request.post(`/admin/catalog/products/${productId}/images`, {
                    image_type: image.imageType?.trim() || 'detail',
                    image_url: imageUrl,
                    sort_order: Number(image.sortOrder) || 0,
                });
            }

            for (const attribute of attributeForms) {
                if (!attribute.attrKey?.trim()) continue;
                await request.post(`/admin/catalog/products/${productId}/attributes`, attributePayload(attribute));
            }

            await onProductChanged?.();
            resetAddForm();
            handleClose();
        } catch (error) {
            setFormError(getApiError(error, 'Có lỗi xảy ra!'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose} size="xl" contentClassName="admin-add-modal">
            <Modal.Header closeButton>
                <Modal.Title>Thêm Sản Phẩm</Modal.Title>
            </Modal.Header>
            <Modal.Body className={cx('product-edit-body')}>
                <div className={cx('product-edit-box-title')}>
                    <h4>Thêm Sản Phẩm</h4>
                </div>
                {formError && <div className="alert alert-danger mb-0">{formError}</div>}
                <section className={cx('product-edit-section')}>
                    <h5>Bảng products</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>External ID<input type="number" className="form-control" value={form.externalId} onChange={(e) => updateForm('externalId', e.target.value)} /></label>
                        <label>Article number<input type="text" className="form-control" value={form.articleNumber} onChange={(e) => updateForm('articleNumber', e.target.value)} /></label>
                        <label>Title<input type="text" className="form-control" value={form.title} onChange={(e) => updateForm('title', e.target.value)} /></label>
                        <label>Tên sản phẩm<input type="text" className="form-control" value={form.titleVi} onChange={(e) => updateForm('titleVi', e.target.value)} /></label>
                        <label>Brand<input type="text" className="form-control" value={form.brand} onChange={(e) => updateForm('brand', e.target.value)} list="brand-list" /></label>
                        <label>Catalog add date<input type="datetime-local" className="form-control" value={form.catalogAddDate} onChange={(e) => updateForm('catalogAddDate', e.target.value)} /></label>
                    </div>
                    <div className={cx('image-upload-field')}>
                        <label>Main image URL<input type="text" className="form-control" value={form.mainImage} onChange={(e) => updateForm('mainImage', e.target.value)} /></label>
                        <label>Main image file<input type="file" className="form-control" accept="image/jpeg,image/png,image/webp,image/gif,image/bmp" onChange={(e) => setMainImageFile(e.target.files?.[0] || null)} /></label>
                    </div>
                    <div className={cx('product-edit-grid')}>
                        <label>Description<textarea className="form-control" value={form.description} onChange={(e) => updateForm('description', e.target.value)} /></label>
                        <label>Mô tả<textarea className="form-control" value={form.descriptionVi} onChange={(e) => updateForm('descriptionVi', e.target.value)} /></label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Bảng product_categories và thuộc tính products</h5>
                    <label>Danh mục</label>
                    <div className={cx('category-multiselect')}>
                        <CategoryTreeSelect
                            nodes={buildCategoryTree(categories.concat(localNewCategories))}
                            selectedIds={selectedCategoryIds}
                            onToggle={toggleCategory}
                            onDeleteLocal={(id) => {
                                const s = String(id);
                                const getDescendants = (parentId, list) => {
                                    let descendants = [];
                                    const children = list.filter(c => String(c.parent_id) === String(parentId));
                                    children.forEach(child => {
                                        descendants.push(String(child.id));
                                        descendants = descendants.concat(getDescendants(child.id, list));
                                    });
                                    return descendants;
                                };
                                setLocalNewCategories((cur) => {
                                    const toDeleteIds = new Set([s, ...getDescendants(s, cur)]);
                                    setSelectedCategoryIds((selected) => selected.filter(x => !toDeleteIds.has(x)));
                                    return cur.filter(x => !toDeleteIds.has(String(x.id)));
                                });
                            }}
                        />
                        <div style={{ marginTop: 12, padding: '12px', border: '1px solid #ddd', borderRadius: '6px', backgroundColor: '#fdfdfd' }}>
                            <div style={{ fontWeight: '600', fontSize: '13px', color: '#444', marginBottom: 8 }}>Thêm danh mục mới vào cây:</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="Tên danh mục..."
                                    value={newCategoryName}
                                    onChange={(e) => setNewCategoryName(e.target.value)}
                                    style={{ flex: '1 1 200px' }}
                                />
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="Category name in English..."
                                    value={newCategoryNameEn}
                                    onChange={(e) => setNewCategoryNameEn(e.target.value)}
                                    style={{ flex: '1 1 200px' }}
                                />
                                <select
                                    className="form-select"
                                    value={newCategoryParentId}
                                    onChange={(e) => setNewCategoryParentId(e.target.value)}
                                    style={{ flex: '1 1 250px' }}
                                >
                                    <option value="">-- Chọn danh mục cha (Không bắt buộc) --</option>
                                    {categories.concat(localNewCategories).map((c) => (
                                        <option key={c.id} value={c.id}>
                                            {getCategoryPath(c, categories.concat(localNewCategories))}
                                        </option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    className="btn btn-outline-primary"
                                    disabled={!newCategoryName.trim() || !newCategoryNameEn.trim()}
                                    onClick={() => {
                                        const nameVi = newCategoryName.trim();
                                        const nameEn = newCategoryNameEn.trim();
                                        const parentId = newCategoryParentId || null;
                                        const combined = [...categories, ...localNewCategories];
                                        
                                        const existing = findCategoryByLabel(combined, nameVi) || findCategoryByLabel(combined, nameEn);
                                        if (existing) {
                                            const existingId = String(existing.value || existing.id);
                                            setSelectedCategoryIds((cur) => (cur.includes(existingId) ? cur : [...cur, existingId]));
                                            setNewCategoryName('');
                                            setNewCategoryNameEn('');
                                            setNewCategoryParentId('');
                                            return;
                                        }

                                        const tempId = `temp-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
                                        const item = {
                                            id: tempId,
                                            label: nameVi,
                                            name: nameEn,
                                            name_vi: nameVi,
                                            value: tempId,
                                            parent_id: parentId,
                                            isNew: true
                                        };

                                        setLocalNewCategories((cur) => [...cur, item]);
                                        setSelectedCategoryIds((cur) => [...cur, tempId]);
                                        setNewCategoryName('');
                                        setNewCategoryNameEn('');
                                        setNewCategoryParentId('');
                                    }}
                                >
                                    Thêm
                                </button>
                            </div>
                        </div>
                    </div>
                    <div className={cx('product-edit-grid')}>
                        <label>Variant name<input type="text" className="form-control" value={form.variantName} onChange={(e) => updateForm('variantName', e.target.value)} /></label>
                        <label>Loại sản phẩm<input type="text" className="form-control" value={form.variantNameVi} onChange={(e) => updateForm('variantNameVi', e.target.value)} /></label>
                        <label>Age group<input type="text" className="form-control" value={form.ageGroup} onChange={(e) => updateForm('ageGroup', e.target.value)} list="agegroup-list" /></label>
                        <label>Nhóm tuổi<input type="text" className="form-control" value={form.ageGroupVi} onChange={(e) => updateForm('ageGroupVi', e.target.value)} list="agegroupvi-list" /></label>
                        <label>Gender
                            <select className="form-select" value={form.gender} onChange={(e) => updateForm('gender', e.target.value)}>
                                <option value="">-- Select Gender --</option>
                                {existingData.genders.map(g => <option key={g} value={g}>{g}</option>)}
                            </select>
                        </label>
                        <label>Giới tính
                            <select className="form-select" value={form.genderVi} onChange={(e) => updateForm('genderVi', e.target.value)}>
                                <option value="">-- Chọn giới tính --</option>
                                {existingData.gendersVi.map(g => <option key={g} value={g}>{g}</option>)}
                            </select>
                        </label>
                        <label>Base colour<input type="text" className="form-control" value={form.baseColour} onChange={(e) => updateForm('baseColour', e.target.value)} /></label>
                        <label>Màu chính<input type="text" className="form-control" value={form.baseColourVi} onChange={(e) => updateForm('baseColourVi', e.target.value)} /></label>
                        <label>Colour 1<input type="text" className="form-control" value={form.colour1} onChange={(e) => updateForm('colour1', e.target.value)} /></label>
                        <label>Màu 1<input type="text" className="form-control" value={form.colour1Vi} onChange={(e) => updateForm('colour1Vi', e.target.value)} /></label>
                        <label>Colour 2<input type="text" className="form-control" value={form.colour2} onChange={(e) => updateForm('colour2', e.target.value)} /></label>
                        <label>Màu 2<input type="text" className="form-control" value={form.colour2Vi} onChange={(e) => updateForm('colour2Vi', e.target.value)} /></label>
                        <label>Season
                            <select className="form-select" value={form.season} onChange={(e) => updateForm('season', e.target.value)}>
                                <option value="">-- Choose the season --</option>
                                {existingData.seasons.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </label>
                        <label>Mùa
                            <select className="form-select" value={form.seasonVi} onChange={(e) => updateForm('seasonVi', e.target.value)}>
                                <option value="">-- Chọn mùa --</option>
                                {existingData.seasonsVi.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </label>
                        <label>Year<input type="number" className="form-control" value={form.year} onChange={(e) => updateForm('year', e.target.value)} /></label>
                        <label>Usage<input type="text" className="form-control" value={form.usage} onChange={(e) => updateForm('usage', e.target.value)} list="usage-list" /></label>
                        <label>Mục đích dùng<input type="text" className="form-control" value={form.usageVi} onChange={(e) => updateForm('usageVi', e.target.value)} list="usagevi-list" /></label>
                        <label>Material<input type="text" className="form-control" value={form.material} onChange={(e) => updateForm('material', e.target.value)} list="material-list" /></label>
                        <label>Chất liệu<input type="text" className="form-control" value={form.materialVi} onChange={(e) => updateForm('materialVi', e.target.value)} list="materialvi-list" /></label>
                        <label>Fit<input type="text" className="form-control" value={form.fit} onChange={(e) => updateForm('fit', e.target.value)} list="fit-list" /></label>
                        <label>Form dáng<input type="text" className="form-control" value={form.fitVi} onChange={(e) => updateForm('fitVi', e.target.value)} list="fitvi-list" /></label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Bảng product_prices</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>Giá bán (Selling price)<input type="number" className="form-control" value={priceForm.sellingPrice} onChange={(e) => updatePriceForm('sellingPrice', e.target.value)} /></label>
                        <label>Giá nhập (Import price)<input type="number" className="form-control" value={priceForm.importPrice} onChange={(e) => updatePriceForm('importPrice', e.target.value)} /></label>
                        <label>VAT<input type="number" className="form-control" value={priceForm.vat} onChange={(e) => updatePriceForm('vat', e.target.value)} /></label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Bảng product_variants</h5>
                    <button type="button" className="btn btn-outline-primary btn-sm mb-2" onClick={addVariantForm}>Thêm size</button>
                    <div className={cx('product-image-list')}>
                        {variantForms.map((variant, index) => (
                            <div className={cx('product-image-row')} key={`add-variant-${index}`}>
                                <div className={cx('product-edit-grid')}>
                                    <label>SKU ID<input type="number" className="form-control" value={variant.skuId} onChange={(e) => updateVariantForm(index, 'skuId', e.target.value)} /></label>
                                    <label>Option name<input type="text" className="form-control" value={variant.optionName} onChange={(e) => updateVariantForm(index, 'optionName', e.target.value)} list="optionname-list" /></label>
                                    <label>Option value<input type="text" className="form-control" value={variant.optionValue} onChange={(e) => updateVariantForm(index, 'optionValue', e.target.value)} list="optionvalue-list" /></label>
                                    <label>Unified size<input type="text" className="form-control" value={variant.unifiedSize} onChange={(e) => updateVariantForm(index, 'unifiedSize', e.target.value)} list="unifiedsize-list" /></label>
                                    <label>Inventory count<input type="number" className="form-control" value={variant.inventoryCount} onChange={(e) => updateVariantForm(index, 'inventoryCount', e.target.value)} /></label>
                                </div>
                                <div className={cx('form-checkbox')}>
                                    <label><input type="checkbox" checked={variant.available} onChange={(e) => updateVariantForm(index, 'available', e.target.checked)} /> Available</label>
                                    <label><input type="checkbox" checked={variant.active} onChange={(e) => updateVariantForm(index, 'active', e.target.checked)} /> Active</label>
                                </div>
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => removeVariantForm(index)} disabled={variantForms.length <= 1}>Xóa size này</button>
                            </div>
                        ))}
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <div className={cx('product-edit-section-head')}>
                        <h5>Bảng product_images</h5>
                        <button type="button" className="btn btn-outline-primary btn-sm" onClick={addImageForm}>Thêm ảnh</button>
                    </div>
                    {imageForms.length === 0 && <p className={cx('empty-image-text')}>Chưa có ảnh phụ.</p>}
                    <div className={cx('product-image-list')}>
                        {imageForms.map((image, index) => (
                            <div className={cx('product-image-row')} key={`add-image-${index}`}>
                                <div className={cx('product-edit-grid')}>
                                    <label>Image type (image_type)<input type="text" className="form-control" placeholder="detail" value={image.imageType} onChange={(e) => updateImageForm(index, 'imageType', e.target.value)} /></label>
                                    <label>Sort order<input type="number" className="form-control" value={image.sortOrder} onChange={(e) => updateImageForm(index, 'sortOrder', e.target.value)} /></label>
                                </div>
                                <label>Image URL<input type="text" className="form-control" value={image.imageUrl} onChange={(e) => updateImageForm(index, 'imageUrl', e.target.value)} /></label>
                                <label>Image file<input type="file" className="form-control" accept="image/jpeg,image/png,image/webp,image/gif,image/bmp" onChange={(e) => updateImageForm(index, 'file', e.target.files?.[0] || null)} /></label>
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => removeImageForm(index)}>Xóa ảnh này</button>
                            </div>
                        ))}
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <div className={cx('product-edit-section-head')}>
                        <h5>Bảng product_attributes</h5>
                        <button type="button" className="btn btn-outline-primary btn-sm" onClick={addAttributeForm}>Thêm thuộc tính</button>
                    </div>
                    {attributeForms.length === 0 && <p className={cx('empty-image-text')}>Chưa có thuộc tính mở rộng.</p>}
                    <div className={cx('product-image-list')}>
                        {attributeForms.map((attribute, index) => (
                            <div className={cx('product-image-row')} key={`add-attribute-${index}`}>
                                <label>Key<input type="text" className="form-control" value={attribute.attrKey} onChange={(e) => updateAttributeForm(index, 'attrKey', e.target.value)} /></label>
                                <div className={cx('product-edit-grid')}>
                                    <label>Value<textarea className="form-control" value={attribute.attrValue} onChange={(e) => updateAttributeForm(index, 'attrValue', e.target.value)} /></label>
                                    <label>Value VI<textarea className="form-control" value={attribute.attrValueVi} onChange={(e) => updateAttributeForm(index, 'attrValueVi', e.target.value)} /></label>
                                </div>
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => removeAttributeForm(index)}>Xóa thuộc tính này</button>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Add product datalists for suggestions */}
                <datalist id="brand-list">
                    {existingData.brands.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="agegroup-list">
                    {existingData.ageGroups.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="agegroupvi-list">
                    {existingData.ageGroupsVi.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="usage-list">
                    {existingData.usages.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="usagevi-list">
                    {existingData.usagesVi.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="material-list">
                    {existingData.materials.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="materialvi-list">
                    {existingData.materialsVi.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="fit-list">
                    {existingData.fits.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="fitvi-list">
                    {existingData.fitsVi.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="optionname-list">
                    {existingData.optionNames.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="optionvalue-list">
                    {existingData.optionValues.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="unifiedsize-list">
                    {existingData.unifiedSizes.map(x => <option key={x} value={x} />)}
                </datalist>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose}>Đóng</Button>
                <Button variant="primary" onClick={handleAddProduct} disabled={saving}>{saving ? 'Đang thêm...' : 'Thêm Sản Phẩm'}</Button>
            </Modal.Footer>
        </Modal>
    );
}
// =================== Xóa Sản Phẩm ===================
export function ModalDeleteProduct({ showModalDelete, setShowModalDelete, idProduct, onProductChanged }) {
    const handleClose = () => setShowModalDelete(false);
    const [deleting, setDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState('');

    useEffect(() => {
        if (showModalDelete) {
            setDeleteError('');
            setDeleting(false);
        }
    }, [showModalDelete, idProduct]);

    const handleDeleteProduct = async () => {
        const productId = Number(idProduct);
        if (!Number.isFinite(productId)) {
            setDeleteError('Không tìm thấy ID sản phẩm cần xóa.');
            return;
        }
        if (!window.confirm(`Xác nhận lần 2: xóa chính thức sản phẩm có ID ${productId}?`)) {
            return;
        }

        try {
            setDeleting(true);
            setDeleteError('');
            await request.delete(`/admin/catalog/products/${productId}`);
            await onProductChanged?.();
            handleClose();
        } catch (error) {
            if (error?.response?.status === 404) {
                await onProductChanged?.();
                handleClose();
                return;
            }
            setDeleteError(getApiError(error, 'Xóa sản phẩm thất bại'));
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Modal show={showModalDelete} onHide={handleClose}>
            <Modal.Header closeButton>
                <Modal.Title>Xóa Sản Phẩm</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <div className={cx('product-edit-box-title')}>
                    <h4>Xóa Sản Phẩm</h4>
                    <p>Bạn chắc chắn muốn xóa sản phẩm có ID: {idProduct}?</p>
                </div>
                {deleteError && <div className="alert alert-danger mb-0">{deleteError}</div>}
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose} disabled={deleting}>Đóng</Button>
                <Button variant="danger" onClick={handleDeleteProduct} disabled={deleting}>
                    {deleting ? 'Đang xóa...' : 'Xóa'}
                </Button>
            </Modal.Footer>
        </Modal>
    );
}

// =================== Sửa Sản Phẩm ===================
const emptyProductForm = {
    externalId: '',
    articleNumber: '',
    title: '',
    titleVi: '',
    brand: '',
    variantName: '',
    variantNameVi: '',
    ageGroup: '',
    ageGroupVi: '',
    gender: '',
    genderVi: '',
    baseColour: '',
    baseColourVi: '',
    colour1: '',
    colour1Vi: '',
    colour2: '',
    colour2Vi: '',
    season: '',
    seasonVi: '',
    year: '',
    usage: '',
    usageVi: '',
    material: '',
    materialVi: '',
    fit: '',
    fitVi: '',
    mainImage: '',
    description: '',
    descriptionVi: '',
    catalogAddDate: '',
};

function toDateTimeLocalValue(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return localDate.toISOString().slice(0, 16);
}

function toInstantValue(value) {
    return value ? new Date(value).toISOString() : null;
}

function numberOrNull(value) {
    if (value === '' || value === null || value === undefined) return null;
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue : null;
}

const emptyVariantForm = {
    skuId: '',
    optionName: '',
    optionValue: '',
    unifiedSize: '',
    inventoryCount: 0,
    available: true,
    active: true,
};

function newVariantForm(defaults = {}) {
    return {
        ...emptyVariantForm,
        ...defaults,
    };
}

function isVariantFormBlank(variant) {
    return (
        !variant.skuId &&
        !variant.optionName?.trim() &&
        !variant.optionValue?.trim() &&
        !variant.unifiedSize?.trim() &&
        Number(variant.inventoryCount || 0) === 0 &&
        Boolean(variant.available) === true &&
        Boolean(variant.active) === true
    );
}

function variantPayload(variant, form) {
    return {
        sku_id: numberOrNull(variant.skuId),
        option_name: variant.optionName || 'default',
        option_value: variant.optionValue || form.variantNameVi || form.variantName || 'default',
        unified_size: variant.unifiedSize || variant.optionValue || 'default',
        inventory_count: Number(variant.inventoryCount) || 0,
        available: Boolean(variant.available),
        active: Boolean(variant.active),
    };
}

function attributePayload(attribute) {
    return {
        attr_key: attribute.attrKey?.trim() || '',
        attr_value: attribute.attrValue,
        attr_value_vi: attribute.attrValueVi,
    };
}

function imageFormFromResponse(image) {
    return {
        id: image.id || null,
        imageType: image.image_type ?? 'detail',
        imageUrl: image.image_url ?? '',
        sortOrder: Number(image.sort_order ?? 0),
        file: null,
        originalImageType: image.image_type ?? 'detail',
        originalImageUrl: image.image_url ?? '',
        originalSortOrder: Number(image.sort_order ?? 0),
    };
}

function variantFormFromResponse(variant) {
    return {
        id: variant.id || null,
        skuId: variant.sku_id ?? '',
        optionName: variant.option_name ?? '',
        optionValue: variant.option_value ?? '',
        unifiedSize: variant.unified_size ?? '',
        inventoryCount: Number(variant.inventory_count ?? 0),
        available: variant.available ?? true,
        active: variant.active ?? true,
        originalSkuId: variant.sku_id ?? '',
        originalOptionName: variant.option_name ?? '',
        originalOptionValue: variant.option_value ?? '',
        originalUnifiedSize: variant.unified_size ?? '',
        originalInventoryCount: Number(variant.inventory_count ?? 0),
        originalAvailable: variant.available ?? true,
        originalActive: variant.active ?? true,
    };
}

function attributeFormFromResponse(attribute) {
    return {
        id: attribute.id || null,
        attrKey: attribute.attr_key ?? '',
        attrValue: attribute.attr_value ?? '',
        attrValueVi: attribute.attr_value_vi ?? '',
        originalAttrKey: attribute.attr_key ?? '',
        originalAttrValue: attribute.attr_value ?? '',
        originalAttrValueVi: attribute.attr_value_vi ?? '',
    };
}

function hasImageChanged(image) {
    return (
        image.imageType !== image.originalImageType ||
        image.imageUrl !== image.originalImageUrl ||
        Number(image.sortOrder || 0) !== Number(image.originalSortOrder || 0)
    );
}

function hasVariantChanged(variant) {
    return (
        numberOrNull(variant.skuId) !== numberOrNull(variant.originalSkuId) ||
        variant.optionName !== variant.originalOptionName ||
        variant.optionValue !== variant.originalOptionValue ||
        variant.unifiedSize !== variant.originalUnifiedSize ||
        Number(variant.inventoryCount || 0) !== Number(variant.originalInventoryCount || 0) ||
        Boolean(variant.available) !== Boolean(variant.originalAvailable) ||
        Boolean(variant.active) !== Boolean(variant.originalActive)
    );
}

function hasAttributeChanged(attribute) {
    return (
        attribute.attrKey !== attribute.originalAttrKey ||
        attribute.attrValue !== attribute.originalAttrValue ||
        attribute.attrValueVi !== attribute.originalAttrValueVi
    );
}

export function ModalEditProduct({ showModalEdit, setShowModalEdit, idProduct, onProductChanged }) {
    const handleClose = () => {
        setNewCategoryNameEdit('');
        setNewCategoryNameEditEn('');
        setNewCategoryParentIdEdit('');
        setLocalNewCategoriesEdit([]);
        setVariantForms([newVariantForm()]);
        setRemovedVariantIds([]);
        setAttributeForms([]);
        setRemovedAttributeIds([]);
        setShowModalEdit(false);
    };

    const [form, setForm] = useState(emptyProductForm);
    const [priceForm, setPriceForm] = useState({ sellingPrice: '', importPrice: '', vat: '0' });
    const [variantForms, setVariantForms] = useState([newVariantForm()]);
    const [removedVariantIds, setRemovedVariantIds] = useState([]);
    const [imageForms, setImageForms] = useState([]);
    const [removedImageIds, setRemovedImageIds] = useState([]);
    const [attributeForms, setAttributeForms] = useState([]);
    const [removedAttributeIds, setRemovedAttributeIds] = useState([]);
    const [mainImageFile, setMainImageFile] = useState(null);
    const [selectedCategoryIds, setSelectedCategoryIds] = useState([]);
    const [allCategories, setAllCategories] = useState([]);
    const [categories, setCategories] = useState([]);
    const [newCategoryNameEdit, setNewCategoryNameEdit] = useState('');
    const [newCategoryNameEditEn, setNewCategoryNameEditEn] = useState('');
    const [newCategoryParentIdEdit, setNewCategoryParentIdEdit] = useState('');
    const [localNewCategoriesEdit, setLocalNewCategoriesEdit] = useState([]);
    const [creatingCategoryEdit, setCreatingCategoryEdit] = useState(false);
    const [editError, setEditError] = useState('');
    const [savingEdit, setSavingEdit] = useState(false);
    const [existingData, setExistingData] = useState({
        brands: [],
        ageGroups: [],
        ageGroupsVi: [],
        usages: [],
        usagesVi: [],
        materials: [],
        materialsVi: [],
        fits: [],
        fitsVi: [],
        optionNames: [],
        optionValues: [],
        unifiedSizes: [],
        genders: [],
        gendersVi: [],
        seasons: [],
        seasonsVi: []
    });

    useEffect(() => {
        if (showModalEdit) {
            request.get('/admin/catalog/products')
                .then((res) => {
                    const products = res.data || [];
                    const brands = new Set();
                    const ageGroups = new Set();
                    const ageGroupsVi = new Set();
                    const usages = new Set();
                    const usagesVi = new Set();
                    const materials = new Set();
                    const materialsVi = new Set();
                    const fits = new Set();
                    const fitsVi = new Set();
                    const optionNames = new Set();
                    const optionValues = new Set();
                    const unifiedSizes = new Set();
                    const gendersSet = new Set();
                    const gendersViSet = new Set();
                    const seasonsSet = new Set();
                    const seasonsViSet = new Set();

                    products.forEach((p) => {
                        if (p.brand) brands.add(String(p.brand).trim());
                        if (p.age_group) ageGroups.add(String(p.age_group).trim());
                        if (p.age_group_vi) ageGroupsVi.add(capitalizeFirstLetter(p.age_group_vi));
                        if (p.usage) usages.add(String(p.usage).trim());
                        if (p.usage_vi) usagesVi.add(capitalizeFirstLetter(p.usage_vi));
                        if (p.material) materials.add(String(p.material).trim());
                        if (p.material_vi) materialsVi.add(capitalizeFirstLetter(p.material_vi));
                        if (p.fit) fits.add(String(p.fit).trim());
                        if (p.fit_vi) fitsVi.add(capitalizeFirstLetter(p.fit_vi));
                        if (p.gender) gendersSet.add(String(p.gender).trim());
                        if (p.gender_vi) gendersViSet.add(capitalizeFirstLetter(p.gender_vi));
                        if (p.season) seasonsSet.add(String(p.season).trim());
                        if (p.season_vi) seasonsViSet.add(capitalizeFirstLetter(p.season_vi));

                        if (Array.isArray(p.variants)) {
                            p.variants.forEach((v) => {
                                if (v.option_name) optionNames.add(String(v.option_name).trim());
                                if (v.option_value) optionValues.add(String(v.option_value).trim());
                                if (v.unified_size) unifiedSizes.add(String(v.unified_size).trim());
                            });
                        }
                    });

                    setExistingData({
                        brands: Array.from(brands),
                        ageGroups: Array.from(ageGroups),
                        ageGroupsVi: Array.from(ageGroupsVi),
                        usages: Array.from(usages),
                        usagesVi: Array.from(usagesVi),
                        materials: Array.from(materials),
                        materialsVi: Array.from(materialsVi),
                        fits: Array.from(fits),
                        fitsVi: Array.from(fitsVi),
                        optionNames: Array.from(optionNames),
                        optionValues: Array.from(optionValues),
                        unifiedSizes: Array.from(unifiedSizes),
                        genders: Array.from(new Set([...defaultGenders, ...gendersSet])),
                        gendersVi: Array.from(new Set([...defaultGendersVi, ...gendersViSet])),
                        seasons: Array.from(new Set([...defaultSeasons, ...seasonsSet])),
                        seasonsVi: Array.from(new Set([...defaultSeasonsVi, ...seasonsViSet])),
                    });
                })
                .catch((err) => console.error('Error fetching existing products data:', err));
        }
    }, [showModalEdit]);

    useEffect(() => {
        if (showModalEdit) {
            fetchAdminCategories({})
                .then((list) => {
                    setAllCategories(list || []);
                    setCategories(buildCategoryOptions(list));
                })
                .catch(() => {
                    setAllCategories([]);
                    setCategories([]);
                });
        }
    }, [showModalEdit]);

    useEffect(() => {
        if (showModalEdit && idProduct) {
            setEditError('');
            request.get(`/admin/catalog/products/${idProduct}`).then((res) => {
                const data = res.data;
                const firstPrice = data?.prices?.[0] || {};
                const variants = data?.variants || [];

                setForm({
                    externalId: data.external_id ?? '',
                    articleNumber: data.article_number ?? '',
                    title: data.title ?? '',
                    titleVi: data.title_vi ?? '',
                    brand: data.brand ?? '',
                    variantName: data.variant_name ?? '',
                    variantNameVi: data.variant_name_vi ?? '',
                    ageGroup: data.age_group ?? '',
                    ageGroupVi: data.age_group_vi ?? '',
                    gender: data.gender ?? '',
                    genderVi: data.gender_vi ?? '',
                    baseColour: data.base_colour ?? '',
                    baseColourVi: data.base_colour_vi ?? '',
                    colour1: data.colour1 ?? '',
                    colour1Vi: data.colour1_vi ?? '',
                    colour2: data.colour2 ?? '',
                    colour2Vi: data.colour2_vi ?? '',
                    season: data.season ?? '',
                    seasonVi: data.season_vi ?? '',
                    year: data.year ?? '',
                    usage: data.usage ?? '',
                    usageVi: data.usage_vi ?? '',
                    material: data.material ?? '',
                    materialVi: data.material_vi ?? '',
                    fit: data.fit ?? '',
                    fitVi: data.fit_vi ?? '',
                    mainImage: data.main_image ?? '',
                    description: data.description ?? '',
                    descriptionVi: data.description_vi ?? '',
                    catalogAddDate: toDateTimeLocalValue(data.catalog_add_date),
                });
                setPriceForm({
                    sellingPrice: firstPrice.selling_price ?? '',
                    importPrice: firstPrice.import_price ?? '',
                    vat: firstPrice.vat ?? '0',
                });
                setVariantForms(variants.length > 0 ? variants.map(variantFormFromResponse) : [newVariantForm()]);
                setRemovedVariantIds([]);
                setImageForms((data?.images || []).map(imageFormFromResponse));
                setRemovedImageIds([]);
                setAttributeForms((data?.attributes || []).map(attributeFormFromResponse));
                setRemovedAttributeIds([]);
                setMainImageFile(null);
                setSelectedCategoryIds((data.category_ids || []).map(String));
                setNewCategoryNameEdit('');
                setNewCategoryNameEditEn('');
                setNewCategoryParentIdEdit('');
                setLocalNewCategoriesEdit([]);
            }).catch((error) => setEditError(getApiError(error, 'Lỗi khi tải dữ liệu sản phẩm')));
        }
    }, [showModalEdit, idProduct]);

    const updateForm = (field, value) => setForm((current) => ({ ...current, [field]: value }));
    const updatePriceForm = (field, value) => setPriceForm((current) => ({ ...current, [field]: value }));
    const updateVariantForm = (index, field, value) => {
        setVariantForms((current) =>
            current.map((variant, variantIndex) => (variantIndex === index ? { ...variant, [field]: value } : variant)),
        );
    };
    const updateImageForm = (index, field, value) => {
        setImageForms((current) =>
            current.map((image, imageIndex) => (imageIndex === index ? { ...image, [field]: value } : image)),
        );
    };
    const updateAttributeForm = (index, field, value) => {
        setAttributeForms((current) =>
            current.map((attribute, attributeIndex) =>
                attributeIndex === index ? { ...attribute, [field]: value } : attribute,
            ),
        );
    };

    const addImageForm = () => {
        setImageForms((current) => [
            ...current,
            {
                id: null,
                imageType: 'detail',
                imageUrl: '',
                sortOrder: current.length,
                originalImageType: 'detail',
                originalImageUrl: '',
                originalSortOrder: current.length,
                file: null,
            },
        ]);
    };

    const removeImageForm = (index) => {
        const removedImage = imageForms[index];
        if (removedImage?.id) {
            setRemovedImageIds((ids) => [...ids, removedImage.id]);
        }
        setImageForms((current) => current.filter((_, imageIndex) => imageIndex !== index));
    };

    const addVariantForm = () => {
        setVariantForms((current) => [...current, newVariantForm()]);
    };

    const removeVariantForm = (index) => {
        const removedVariant = variantForms[index];
        if (removedVariant?.id) {
            setRemovedVariantIds((ids) => [...ids, removedVariant.id]);
        }
        setVariantForms((current) => (current.length > 1 ? current.filter((_, variantIndex) => variantIndex !== index) : current));
    };

    const addAttributeForm = () => {
        setAttributeForms((current) => [
            ...current,
            {
                id: null,
                attrKey: '',
                attrValue: '',
                attrValueVi: '',
                originalAttrKey: '',
                originalAttrValue: '',
                originalAttrValueVi: '',
            },
        ]);
    };

    const removeAttributeForm = (index) => {
        const removedAttribute = attributeForms[index];
        if (removedAttribute?.id) {
            setRemovedAttributeIds((ids) => [...ids, removedAttribute.id]);
        }
        setAttributeForms((current) => current.filter((_, attributeIndex) => attributeIndex !== index));
    };

    const addCategoryId = (id) => setSelectedCategoryIds((cur) => appendCategoryId(cur, id));
    const removeCategoryId = (id) => setSelectedCategoryIds((cur) => cur.filter((x) => x !== String(id)));
    const selectedCategoryItems = selectedCategoryIds.map((categoryId) => ({
        id: categoryId,
        label: categoryLabelById(categories.concat(localNewCategoriesEdit), categoryId),
    }));

    const uploadProductImageFile = async (file) => {
        if (!file) return '';
        const formData = new FormData();
        formData.append('file', file);
        const response = await request.post(`/admin/catalog/products/${idProduct}/images/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        const url = response.data?.url;
        if (!url) throw new Error('cloudinary_url_missing');
        return url;
    };

    const handleEditProduct = async () => {
        try {
            setSavingEdit(true);
            setEditError('');

            let tempToRealMap = {};
            if (localNewCategoriesEdit.length > 0) {
                tempToRealMap = await saveLocalNewCategories(localNewCategoriesEdit);
            }

            const finalCategoryIds = selectedCategoryIds.map((id) => {
                if (String(id).startsWith('temp-')) {
                    return Number(tempToRealMap[id]);
                }
                return Number(id);
            });

            const uploadedMainImage = await uploadProductImageFile(mainImageFile);
            const nextMainImage = uploadedMainImage || form.mainImage;

            await request.put(`/admin/catalog/products/${idProduct}`, {
                external_id: numberOrNull(form.externalId),
                article_number: form.articleNumber,
                title: form.title || form.titleVi || 'San pham',
                title_vi: form.titleVi || form.title,
                brand: form.brand,
                variant_name: form.variantName,
                variant_name_vi: form.variantNameVi,
                age_group: form.ageGroup,
                age_group_vi: form.ageGroupVi,
                gender: form.gender,
                gender_vi: form.genderVi,
                base_colour: form.baseColour,
                base_colour_vi: form.baseColourVi,
                colour1: form.colour1,
                colour1_vi: form.colour1Vi,
                colour2: form.colour2,
                colour2_vi: form.colour2Vi,
                season: form.season,
                season_vi: form.seasonVi,
                year: numberOrNull(form.year),
                usage: form.usage,
                usage_vi: form.usageVi,
                material: form.material,
                material_vi: form.materialVi,
                fit: form.fit,
                fit_vi: form.fitVi,
                main_image: nextMainImage,
                description: form.description,
                description_vi: form.descriptionVi,
                catalog_add_date: toInstantValue(form.catalogAddDate),
                category_ids: finalCategoryIds,
            });

            if (Number(priceForm.sellingPrice) > 0) {
                await request.post(`/admin/catalog/products/${idProduct}/prices`, {
                    selling_price: Number(priceForm.sellingPrice),
                    import_price: numberOrNull(priceForm.importPrice),
                    vat: numberOrNull(priceForm.vat),
                });
            }

            const deletedVariantIds = new Set(removedVariantIds.filter(Boolean));
            await Promise.all(
                Array.from(deletedVariantIds).map((removedVariantId) =>
                    request.delete(`/admin/catalog/products/${idProduct}/variants/${removedVariantId}`),
                ),
            );

            for (const variant of variantForms) {
                if (deletedVariantIds.has(variant.id)) {
                    continue;
                }

                if (!variant.id && isVariantFormBlank(variant)) {
                    continue;
                }

                const payload = variantPayload(variant, form);
                if (variant.id) {
                    if (hasVariantChanged(variant)) {
                        await request.put(`/admin/catalog/products/${idProduct}/variants/${variant.id}`, payload);
                    }
                } else {
                    await request.post(`/admin/catalog/products/${idProduct}/variants`, payload);
                }
            }

            const deletedImageIds = new Set(removedImageIds.filter(Boolean));
            await Promise.all(
                Array.from(deletedImageIds).map((removedImageId) =>
                    request.delete(`/admin/catalog/products/${idProduct}/images/${removedImageId}`),
                ),
            );

            for (const image of imageForms) {
                const uploadedImageUrl = await uploadProductImageFile(image.file);
                const nextImageUrl = uploadedImageUrl || image.imageUrl?.trim();
                const imageChanged = hasImageChanged(image) || Boolean(uploadedImageUrl);
                if (image.id && !nextImageUrl && !deletedImageIds.has(image.id)) {
                    await request.delete(`/admin/catalog/products/${idProduct}/images/${image.id}`);
                    deletedImageIds.add(image.id);
                    continue;
                }

                if (image.id && (!imageChanged || deletedImageIds.has(image.id))) {
                    continue;
                }

                if (image.id && imageChanged) {
                    await request.delete(`/admin/catalog/products/${idProduct}/images/${image.id}`);
                    deletedImageIds.add(image.id);
                }

                if (nextImageUrl) {
                    await request.post(`/admin/catalog/products/${idProduct}/images`, {
                        image_type: image.imageType?.trim() || 'detail',
                        image_url: nextImageUrl,
                        sort_order: Number(image.sortOrder) || 0,
                    });
                }
            }

            const deletedAttributeIds = new Set(removedAttributeIds.filter(Boolean));
            await Promise.all(
                Array.from(deletedAttributeIds).map((removedAttributeId) =>
                    request.delete(`/admin/catalog/products/${idProduct}/attributes/${removedAttributeId}`),
                ),
            );

            for (const attribute of attributeForms) {
                const attrKey = attribute.attrKey?.trim();

                if (attribute.id && !attrKey && !deletedAttributeIds.has(attribute.id)) {
                    await request.delete(`/admin/catalog/products/${idProduct}/attributes/${attribute.id}`);
                    deletedAttributeIds.add(attribute.id);
                    continue;
                }

                if (!attrKey || deletedAttributeIds.has(attribute.id)) {
                    continue;
                }

                const payload = attributePayload(attribute);
                if (attribute.id) {
                    if (hasAttributeChanged(attribute)) {
                        await request.put(`/admin/catalog/products/${idProduct}/attributes/${attribute.id}`, payload);
                    }
                } else {
                    await request.post(`/admin/catalog/products/${idProduct}/attributes`, payload);
                }
            }

            await onProductChanged?.();
            handleClose();
        } catch (error) {
            setEditError(getApiError(error, 'Lỗi khi chỉnh sửa sản phẩm'));
        } finally {
            setSavingEdit(false);
        }
    };

    return (
        <Modal show={showModalEdit} onHide={handleClose} size="xl" contentClassName="admin-edit-modal">
            <Modal.Header closeButton>
                <Modal.Title>Sửa Sản Phẩm</Modal.Title>
            </Modal.Header>
            <Modal.Body className={cx('product-edit-body')}>
                {editError && <div className="alert alert-danger mb-0">{editError}</div>}
                <div className={cx('product-edit-box-title')}>
                    <h4>Sửa Sản Phẩm{form.title ? ` - ${form.title}` : ''}</h4>
                </div>
                <section className={cx('product-edit-section')}>
                    <h5>Thông tin chính</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>External ID<input type="number" className="form-control" value={form.externalId} onChange={(e) => updateForm('externalId', e.target.value)} /></label>
                        <label>Article number<input type="text" className="form-control" value={form.articleNumber} onChange={(e) => updateForm('articleNumber', e.target.value)} /></label>
                        <label>Title<input type="text" className="form-control" value={form.title} onChange={(e) => updateForm('title', e.target.value)} /></label>
                        <label>Tên sản phẩm<input type="text" className="form-control" value={form.titleVi} onChange={(e) => updateForm('titleVi', e.target.value)} /></label>
                        <label>Brand<input type="text" className="form-control" value={form.brand} onChange={(e) => updateForm('brand', e.target.value)} list="brand-list" /></label>
                        <label>Catalog add date<input type="datetime-local" className="form-control" value={form.catalogAddDate} onChange={(e) => updateForm('catalogAddDate', e.target.value)} /></label>
                    </div>
                    <div className={cx('image-upload-field')}>
                        <label>Main image URL<input type="text" className="form-control" value={form.mainImage} onChange={(e) => updateForm('mainImage', e.target.value)} /></label>
                        <label>
                            Main image file
                            <input
                                type="file"
                                className="form-control"
                                accept="image/jpeg,image/png,image/webp,image/gif,image/bmp"
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    e.target.value = '';
                                    setMainImageFile(file || null);
                                }}
                            />
                            {mainImageFile && <span className={cx('empty-image-text')}>Đã chọn: {mainImageFile.name}</span>}
                        </label>
                    </div>
                    <div className={cx('product-edit-grid')}>
                        <label>Description<textarea className="form-control" value={form.description} onChange={(e) => updateForm('description', e.target.value)} /></label>
                        <label>Mô tả<textarea className="form-control" value={form.descriptionVi} onChange={(e) => updateForm('descriptionVi', e.target.value)} /></label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Danh mục và thuộc tính</h5>
                    <label>Danh mục đang lưu</label>
                    <div className={cx('saved-category-list')}>
                        {selectedCategoryItems.length === 0 && <p className={cx('empty-image-text')}>Chưa có danh mục.</p>}
                        {selectedCategoryItems.map((category) => (
                            <span key={category.id} className={cx('saved-category-item')}>
                                <span>{category.label}</span>
                                <button type="button" onClick={() => removeCategoryId(category.id)} aria-label={`Bỏ ${category.label}`}>
                                    ×
                                </button>
                            </span>
                        ))}
                    </div>
                    <label>Gợi ý thêm danh mục</label>
                    <div className={cx('category-multiselect')}>
                        <CategoryTreeSelect
                            nodes={buildCategoryTree(categories.concat(localNewCategoriesEdit))}
                            selectedIds={selectedCategoryIds}
                            onToggle={(val) => {
                                const s = String(val);
                                const descendants = getDescendantIds(s, categories.concat(localNewCategoriesEdit));
                                const allSelected = descendants.every((descId) => selectedCategoryIds.includes(descId));
                                setSelectedCategoryIds((cur) => {
                                    if (allSelected) {
                                        return cur.filter((x) => !descendants.includes(x));
                                    } else {
                                        const next = [...cur];
                                        descendants.forEach((descId) => {
                                            if (!next.includes(descId)) {
                                                next.push(descId);
                                            }
                                        });
                                        return next;
                                    }
                                });
                            }}
                            onDeleteLocal={(id) => {
                                const s = String(id);
                                const getDescendants = (parentId, list) => {
                                    let descendants = [];
                                    const children = list.filter(c => String(c.parent_id) === String(parentId));
                                    children.forEach(child => {
                                        descendants.push(String(child.id));
                                        descendants = descendants.concat(getDescendants(child.id, list));
                                    });
                                    return descendants;
                                };
                                setLocalNewCategoriesEdit((cur) => {
                                    const toDeleteIds = new Set([s, ...getDescendants(s, cur)]);
                                    setSelectedCategoryIds((selected) => selected.filter(x => !toDeleteIds.has(x)));
                                    return cur.filter(x => !toDeleteIds.has(String(x.id)));
                                });
                            }}
                        />
                        <div style={{ marginTop: 12, padding: '12px', border: '1px solid #ddd', borderRadius: '6px', backgroundColor: '#fdfdfd' }}>
                            <div style={{ fontWeight: '600', fontSize: '13px', color: '#444', marginBottom: 8 }}>Thêm danh mục mới vào cây:</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="Tên danh mục..."
                                    value={newCategoryNameEdit}
                                    onChange={(e) => setNewCategoryNameEdit(e.target.value)}
                                    style={{ flex: '1 1 200px' }}
                                />
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="Category name in English..."
                                    value={newCategoryNameEditEn}
                                    onChange={(e) => setNewCategoryNameEditEn(e.target.value)}
                                    style={{ flex: '1 1 200px' }}
                                />
                                <select
                                    className="form-select"
                                    value={newCategoryParentIdEdit}
                                    onChange={(e) => setNewCategoryParentIdEdit(e.target.value)}
                                    style={{ flex: '1 1 250px' }}
                                >
                                    <option value="">-- Chọn danh mục cha (Không bắt buộc) --</option>
                                    {categories.concat(localNewCategoriesEdit).map((c) => (
                                        <option key={c.id} value={c.id}>
                                            {getCategoryPath(c, categories.concat(localNewCategoriesEdit))}
                                        </option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    className="btn btn-outline-primary"
                                    disabled={!newCategoryNameEdit.trim() || !newCategoryNameEditEn.trim()}
                                    onClick={() => {
                                        const nameVi = newCategoryNameEdit.trim();
                                        const nameEn = newCategoryNameEditEn.trim();
                                        const parentId = newCategoryParentIdEdit || null;
                                        const combined = [...categories, ...localNewCategoriesEdit];
                                        
                                        const existing = findCategoryByLabel(combined, nameVi) || findCategoryByLabel(combined, nameEn);
                                        if (existing) {
                                            const existingId = String(existing.value || existing.id);
                                            setSelectedCategoryIds((cur) => (cur.includes(existingId) ? cur : [...cur, existingId]));
                                            setNewCategoryNameEdit('');
                                            setNewCategoryNameEditEn('');
                                            setNewCategoryParentIdEdit('');
                                            return;
                                        }

                                        const tempId = `temp-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
                                        const item = {
                                            id: tempId,
                                            label: nameVi,
                                            name: nameEn,
                                            name_vi: nameVi,
                                            value: tempId,
                                            parent_id: parentId,
                                            isNew: true
                                        };

                                        setLocalNewCategoriesEdit((cur) => [...cur, item]);
                                        setSelectedCategoryIds((cur) => [...cur, tempId]);
                                        setNewCategoryNameEdit('');
                                        setNewCategoryNameEditEn('');
                                        setNewCategoryParentIdEdit('');
                                    }}
                                >
                                    Thêm
                                </button>
                            </div>
                        </div>
                    </div>
                    <div className={cx('product-edit-grid')}>
                        <label>Variant name<input type="text" className="form-control" value={form.variantName} onChange={(e) => updateForm('variantName', e.target.value)} /></label>
                        <label>Loại sản phẩm<input type="text" className="form-control" value={form.variantNameVi} onChange={(e) => updateForm('variantNameVi', e.target.value)} /></label>
                        <label>Age group<input type="text" className="form-control" value={form.ageGroup} onChange={(e) => updateForm('ageGroup', e.target.value)} list="agegroup-list" /></label>
                        <label>Nhóm tuổi<input type="text" className="form-control" value={form.ageGroupVi} onChange={(e) => updateForm('ageGroupVi', e.target.value)} list="agegroupvi-list" /></label>
                        <label>Gender
                            <select className="form-select" value={form.gender} onChange={(e) => updateForm('gender', e.target.value)}>
                                <option value="">-- Select Gender --</option>
                                {existingData.genders.map(g => <option key={g} value={g}>{g}</option>)}
                            </select>
                        </label>
                        <label>Giới tính
                            <select className="form-select" value={form.genderVi} onChange={(e) => updateForm('genderVi', e.target.value)}>
                                <option value="">-- Chọn giới tính--</option>
                                {existingData.gendersVi.map(g => <option key={g} value={g}>{g}</option>)}
                            </select>
                        </label>
                        <label>Base colour<input type="text" className="form-control" value={form.baseColour} onChange={(e) => updateForm('baseColour', e.target.value)} /></label>
                        <label>Màu chính<input type="text" className="form-control" value={form.baseColourVi} onChange={(e) => updateForm('baseColourVi', e.target.value)} /></label>
                        <label>Colour 1<input type="text" className="form-control" value={form.colour1} onChange={(e) => updateForm('colour1', e.target.value)} /></label>
                        <label>Màu 1<input type="text" className="form-control" value={form.colour1Vi} onChange={(e) => updateForm('colour1Vi', e.target.value)} /></label>
                        <label>Colour 2<input type="text" className="form-control" value={form.colour2} onChange={(e) => updateForm('colour2', e.target.value)} /></label>
                        <label>Màu 2<input type="text" className="form-control" value={form.colour2Vi} onChange={(e) => updateForm('colour2Vi', e.target.value)} /></label>
                        <label>Season
                            <select className="form-select" value={form.season} onChange={(e) => updateForm('season', e.target.value)}>
                                <option value="">-- Choose the season --</option>
                                {existingData.seasons.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </label>
                        <label>Mùa
                            <select className="form-select" value={form.seasonVi} onChange={(e) => updateForm('seasonVi', e.target.value)}>
                                <option value="">-- Chọn mùa --</option>
                                {existingData.seasonsVi.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </label>
                        <label>Year<input type="number" className="form-control" value={form.year} onChange={(e) => updateForm('year', e.target.value)} /></label>
                        <label>Usage<input type="text" className="form-control" value={form.usage} onChange={(e) => updateForm('usage', e.target.value)} list="usage-list" /></label>
                        <label>Mục đích dùng<input type="text" className="form-control" value={form.usageVi} onChange={(e) => updateForm('usageVi', e.target.value)} list="usagevi-list" /></label>
                        <label>Material<input type="text" className="form-control" value={form.material} onChange={(e) => updateForm('material', e.target.value)} list="material-list" /></label>
                        <label>Chất liệu<input type="text" className="form-control" value={form.materialVi} onChange={(e) => updateForm('materialVi', e.target.value)} list="materialvi-list" /></label>
                        <label>Fit<input type="text" className="form-control" value={form.fit} onChange={(e) => updateForm('fit', e.target.value)} list="fit-list" /></label>
                        <label>Form dáng<input type="text" className="form-control" value={form.fitVi} onChange={(e) => updateForm('fitVi', e.target.value)} list="fitvi-list" /></label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Giá</h5>
                    <div className={cx('product-edit-grid')}>
                        <label>Giá bán (Selling price)<input type="number" className="form-control" value={priceForm.sellingPrice} onChange={(e) => updatePriceForm('sellingPrice', e.target.value)} /></label>
                        <label>Giá nhập (Import price)<input type="number" className="form-control" value={priceForm.importPrice} onChange={(e) => updatePriceForm('importPrice', e.target.value)} /></label>
                        <label>VAT<input type="number" className="form-control" value={priceForm.vat} onChange={(e) => updatePriceForm('vat', e.target.value)} /></label>
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <h5>Biến thể và kho</h5>
                    <button type="button" className="btn btn-outline-primary btn-sm mb-2" onClick={addVariantForm}>Thêm size</button>
                    <div className={cx('product-image-list')}>
                        {variantForms.map((variant, index) => (
                            <div className={cx('product-image-row')} key={variant.id || `new-variant-${index}`}>
                                <div className={cx('product-edit-grid')}>
                                    <label>SKU ID<input type="number" className="form-control" value={variant.skuId} onChange={(e) => updateVariantForm(index, 'skuId', e.target.value)} /></label>
                                    <label>Option name<input type="text" className="form-control" value={variant.optionName} onChange={(e) => updateVariantForm(index, 'optionName', e.target.value)} list="optionname-list" /></label>
                                    <label>Option value<input type="text" className="form-control" value={variant.optionValue} onChange={(e) => updateVariantForm(index, 'optionValue', e.target.value)} list="optionvalue-list" /></label>
                                    <label>Unified size<input type="text" className="form-control" value={variant.unifiedSize} onChange={(e) => updateVariantForm(index, 'unifiedSize', e.target.value)} list="unifiedsize-list" /></label>
                                    <label>Inventory count<input type="number" className="form-control" value={variant.inventoryCount} onChange={(e) => updateVariantForm(index, 'inventoryCount', e.target.value)} /></label>
                                </div>
                                <div className={cx('form-checkbox')}>
                                    <label><input type="checkbox" checked={variant.available} onChange={(e) => updateVariantForm(index, 'available', e.target.checked)} /> Available</label>
                                    <label><input type="checkbox" checked={variant.active} onChange={(e) => updateVariantForm(index, 'active', e.target.checked)} /> Active</label>
                                </div>
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => removeVariantForm(index)} disabled={variantForms.length <= 1}>Xóa size này</button>
                            </div>
                        ))}
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <div className={cx('product-edit-section-head')}>
                        <h5>Ảnh phụ</h5>
                        <button type="button" className="btn btn-outline-primary btn-sm" onClick={addImageForm}>
                            Thêm ảnh
                        </button>
                    </div>
                    {imageForms.length === 0 && <p className={cx('empty-image-text')}>Chưa có ảnh phụ trong product_images.</p>}
                    <div className={cx('product-image-list')}>
                        {imageForms.map((image, index) => (
                            <div className={cx('product-image-row')} key={image.id || `new-image-${index}`}>
                                <div className={cx('product-edit-grid')}>
                                    <label>
                                        Image type (image_type)
                                        <input
                                            type="text"
                                            className="form-control"
                                            placeholder="detail"
                                            value={image.imageType}
                                            onChange={(e) => updateImageForm(index, 'imageType', e.target.value)}
                                        />
                                    </label>
                                    <label>
                                        Sort order
                                        <input
                                            type="number"
                                            className="form-control"
                                            value={image.sortOrder}
                                            onChange={(e) => updateImageForm(index, 'sortOrder', e.target.value)}
                                        />
                                    </label>
                                </div>
                                <label>
                                    Image URL
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={image.imageUrl}
                                        onChange={(e) => updateImageForm(index, 'imageUrl', e.target.value)}
                                    />
                                </label>
                                <label>
                                    Image file
                                    <input
                                        type="file"
                                        className="form-control"
                                        accept="image/jpeg,image/png,image/webp,image/gif,image/bmp"
                                        onChange={(e) => {
                                            const file = e.target.files?.[0];
                                            e.target.value = '';
                                            updateImageForm(index, 'file', file || null);
                                        }}
                                    />
                                    {image.file && <span className={cx('empty-image-text')}>Đã chọn: {image.file.name}</span>}
                                </label>
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => removeImageForm(index)}>
                                    Xóa ảnh này
                                </button>
                            </div>
                        ))}
                    </div>
                </section>

                <section className={cx('product-edit-section')}>
                    <div className={cx('product-edit-section-head')}>
                        <h5>Bang product_attributes</h5>
                        <button type="button" className="btn btn-outline-primary btn-sm" onClick={addAttributeForm}>
                            Thêm thuộc tính
                        </button>
                    </div>
                    {attributeForms.length === 0 && <p className={cx('empty-image-text')}>Chua co thuoc tinh trong product_attributes.</p>}
                    <div className={cx('product-image-list')}>
                        {attributeForms.map((attribute, index) => (
                            <div className={cx('product-image-row')} key={attribute.id || `new-attribute-${index}`}>
                                <label>
                                    Key (attr_key)
                                    <input
                                        type="text"
                                        className="form-control"
                                        value={attribute.attrKey}
                                        onChange={(e) => updateAttributeForm(index, 'attrKey', e.target.value)}
                                    />
                                </label>
                                <div className={cx('product-edit-grid')}>
                                    <label>
                                        Value (attr_value)
                                        <textarea
                                            className="form-control"
                                            value={attribute.attrValue}
                                            onChange={(e) => updateAttributeForm(index, 'attrValue', e.target.value)}
                                        />
                                    </label>
                                    <label>
                                        Value VI (attr_value_vi)
                                        <textarea
                                            className="form-control"
                                            value={attribute.attrValueVi}
                                            onChange={(e) => updateAttributeForm(index, 'attrValueVi', e.target.value)}
                                        />
                                    </label>
                                </div>
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => removeAttributeForm(index)}>
                                    Xóa thuộc tính này
                                </button>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Datalists for suggestions */}
                <datalist id="brand-list">
                    {existingData.brands.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="agegroup-list">
                    {existingData.ageGroups.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="agegroupvi-list">
                    {existingData.ageGroupsVi.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="usage-list">
                    {existingData.usages.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="usagevi-list">
                    {existingData.usagesVi.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="material-list">
                    {existingData.materials.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="materialvi-list">
                    {existingData.materialsVi.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="fit-list">
                    {existingData.fits.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="fitvi-list">
                    {existingData.fitsVi.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="optionname-list">
                    {existingData.optionNames.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="optionvalue-list">
                    {existingData.optionValues.map(x => <option key={x} value={x} />)}
                </datalist>
                <datalist id="unifiedsize-list">
                    {existingData.unifiedSizes.map(x => <option key={x} value={x} />)}
                </datalist>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose} disabled={savingEdit}>Đóng</Button>
                <Button variant="primary" onClick={handleEditProduct} disabled={savingEdit}>
                    {savingEdit ? 'Đang lưu...' : 'Lưu Lại'}
                </Button>
            </Modal.Footer>
        </Modal>
    );
}








