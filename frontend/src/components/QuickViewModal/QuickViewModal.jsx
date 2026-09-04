import React, { useEffect, useMemo, useState } from 'react';
import classNames from 'classnames/bind';
import { Link } from 'react-router-dom';
import { X, ShoppingCart } from 'lucide-react';
import { formatVndFromDb } from '../../utils/price';
import { handleImageFallback, PRODUCT_IMAGE_FALLBACK, resolveImageUrl } from '../../utils/image';
import { isProductPurchasable, isVariantPurchasable, productStock } from '../../utils/stock';
import { titleOf } from '../../utils/productDisplay';
import styles from './QuickViewModal.module.scss';

const cx = classNames.bind(styles);

function galleryOf(product) {
    const urls = [];
    const add = (url) => {
        if (!url || typeof url !== 'string') return;
        const resolved = resolveImageUrl(url);
        if (resolved && !urls.includes(resolved)) urls.push(resolved);
    };

    add(product?.main_image || product?.mainImage);
    add(product?.image_url || product?.imageUrl);
    if (Array.isArray(product?.image_urls)) product.image_urls.forEach(add);
    if (Array.isArray(product?.imageUrls)) product.imageUrls.forEach(add);
    if (Array.isArray(product?.images)) {
        product.images.forEach((image) => {
            add(typeof image === 'string' ? image : image?.image_url || image?.imageUrl || image?.url);
        });
    }
    add(product?.img);

    return urls.length > 0 ? urls : [PRODUCT_IMAGE_FALLBACK];
}

function QuickViewModal({ product, open, onClose, onAddToCart }) {
    const [selectedVariantId, setSelectedVariantId] = useState('');
    const [activeImage, setActiveImage] = useState('');

    const variants = useMemo(() => product?.variants || [], [product]);
    const gallery = useMemo(() => galleryOf(product), [product]);

    useEffect(() => {
        if (!product) return;
        const firstAvailable = variants.find(isVariantPurchasable) || variants[0];
        setSelectedVariantId(firstAvailable?.id ? String(firstAvailable.id) : '');
        setActiveImage(gallery[0] || '');
    }, [product, gallery, variants]);

    useEffect(() => {
        if (!open) return undefined;
        const onKey = (event) => {
            if (event.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    if (!open || !product) return null;

    const selectedVariant = variants.find((v) => String(v.id) === String(selectedVariantId));
    const totalStock = productStock(product, selectedVariant);
    const isAvailable = isProductPurchasable(product, selectedVariant);

    const originalPrice = product.price && (typeof product.price === 'object' ? product.price.price : product.price);
    const currentPrice = product.priceNew;
    const hasDiscount = originalPrice && currentPrice && Number(currentPrice) < Number(originalPrice);
    const discountPercent = hasDiscount ? Math.round(((originalPrice - currentPrice) / originalPrice) * 100) : 0;

    const handleAdd = () => {
        onAddToCart({ ...product, productVariantId: selectedVariant?.id || null, selectedVariant, quantity: 1 });
    };

    return (
        <div className={cx('overlay')} onClick={onClose} role="presentation">
            <div className={cx('modal')} onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
                <button type="button" className={cx('close')} onClick={onClose} aria-label="Đóng">
                    <X size={20} />
                </button>

                <div className={cx('body')}>
                    <div className={cx('gallery')}>
                        <div className={cx('main-image')}>
                            {activeImage ? (
                                <img src={activeImage} alt={titleOf(product)} onError={handleImageFallback} />
                            ) : (
                                <div className={cx('placeholder')}>Chưa có ảnh</div>
                            )}
                            {hasDiscount && <span className={cx('discount')}>-{discountPercent}%</span>}
                        </div>
                        {gallery.length > 1 && (
                            <div className={cx('thumbs')}>
                                {gallery.map((src, index) => (
                                    <button
                                        key={src}
                                        type="button"
                                        className={cx('thumb', src === activeImage && 'thumb-active')}
                                        onClick={() => setActiveImage(src)}
                                        aria-label={`Ảnh ${index + 1}`}
                                    >
                                        <img src={src} alt={`${titleOf(product)} ${index + 1}`} onError={handleImageFallback} />
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className={cx('info')}>
                        <p className={cx('brand')}>{product.brand || product.author || 'Sản phẩm'}</p>
                        <h2 className={cx('name')}>{titleOf(product)}</h2>

                        <div className={cx('price-row')}>
                            <span className={cx('price')}>{formatVndFromDb(currentPrice)}</span>
                            {hasDiscount && <span className={cx('original')}>{formatVndFromDb(originalPrice)}</span>}
                        </div>

                        {variants.length > 0 && (
                            <label className={cx('variant')}>
                                Lựa chọn
                                <select value={selectedVariantId} onChange={(event) => setSelectedVariantId(event.target.value)}>
                                    {variants.map((variant) => (
                                        <option key={variant.id} value={variant.id}>
                                            {variant.unified_size || variant.option_value || `Mẫu ${variant.id}`} - còn {variant.inventory_count ?? 0}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        )}

                        <div className={cx('stock', !isAvailable && 'stock-empty')}>
                            {isAvailable ? `Còn hàng: ${totalStock}` : 'Hết hàng'}
                        </div>

                        <div className={cx('actions')}>
                            <button type="button" className={cx('add-btn')} disabled={!isAvailable} onClick={handleAdd}>
                                <ShoppingCart size={18} />
                                {isAvailable ? 'Thêm vào giỏ' : 'Hết hàng'}
                            </button>
                            <Link to={`/prodetail/${product.id}`} className={cx('detail-link')} onClick={onClose}>
                                Xem chi tiết
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default QuickViewModal;
