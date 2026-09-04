import React, { useEffect, useState } from 'react';
import classNames from 'classnames/bind';
import { Link, useNavigate } from 'react-router-dom';
import { X, ShoppingCart } from 'lucide-react';
import { useDispatch } from 'react-redux';

import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import Banner from '../Layouts/Banner/Banner';
import EmptyState from '../../components/EmptyState/EmptyState';
import { useCompare } from '../../utils/useCompare';
import { removeFromCompare, clearCompare } from '../../utils/compare';
import { fetchCatalogProduct } from '../../api/catalogApi';
import { addProduct } from '../../redux/actions';
import { formatVndFromDb } from '../../utils/price';
import { handleImageFallback, resolveImageUrl } from '../../utils/image';
import { isProductPurchasable, pickPurchasableVariant, productStock } from '../../utils/stock';
import styles from './ProductComparison.module.scss';
import { titleOf } from '../../utils/productDisplay';

const cx = classNames.bind(styles);

function brandOf(product) {
    return product?.brand || product?.brand_name || product?.brandName || 'Đang cập nhật';
}

function sizesOf(product) {
    const sizes = (product?.variants || [])
        .map((v) => v.unified_size || v.option_value)
        .filter(Boolean);
    return sizes.length ? Array.from(new Set(sizes)).join(', ') : 'Đang cập nhật';
}

function ratingOf(product) {
    const value = Number(
        product?.review_summary?.average_rating ??
            product?.review_summary?.averageRating ??
            0,
    );
    return value > 0 ? `${value.toFixed(1)} / 5` : 'Chưa có';
}

function ProductComparison() {
    const compareItems = useCompare();
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const [details, setDetails] = useState({});
    const [loading, setLoading] = useState(true);
    const [notice, setNotice] = useState(null);

    const showNotice = (message, type = 'success') => {
        setNotice({ message, type });
        window.clearTimeout(showNotice.timeoutId);
        showNotice.timeoutId = window.setTimeout(() => setNotice(null), 2600);
    };

    useEffect(() => {
        let mounted = true;

        async function loadDetails() {
            setLoading(true);
            const ids = compareItems.map((item) => item.id);
            const entries = await Promise.all(ids.map(async (id) => {
                try {
                    return [id, await fetchCatalogProduct(id)];
                } catch {
                    return [id, null];
                }
            }));
            if (mounted) {
                setDetails(Object.fromEntries(entries));
                setLoading(false);
            }
        }

        if (compareItems.length) {
            loadDetails();
        } else {
            setDetails({});
            setLoading(false);
        }

        return () => {
            mounted = false;
        };
    }, [compareItems]);

    const handleAddToCart = (product) => {
        const selectedVariant = pickPurchasableVariant(product);
        if (!isProductPurchasable(product, selectedVariant)) {
            showNotice('Sản phẩm hiện không còn hàng.', 'error');
            return;
        }
        dispatch(addProduct({
            ...product,
            productVariantId: selectedVariant?.id || null,
            selectedVariant,
            quantity: 1,
        }));
        showNotice('Đã thêm vào giỏ hàng.');
    };

    if (!compareItems.length) {
        return (
            <div className={cx('wrapper')}>
                <header><Header /></header>
                <div><Banner /></div>
                <main className={cx('inner')}>
                    <EmptyState
                        type="search"
                        title="Chưa có sản phẩm để so sánh"
                        description="Hãy thêm sản phẩm vào danh sách so sánh để xem các thông số cạnh nhau."
                        actionText="Khám phá sản phẩm"
                        actionLink="/category"
                    />
                </main>
                <footer><Footer /></footer>
            </div>
        );
    }

    const rows = [
        { label: 'Giá', render: (p, item) => formatVndFromDb(p?.priceNew ?? item.priceNew) },
        { label: 'Thương hiệu', render: (p) => brandOf(p) },
        { label: 'Đánh giá', render: (p) => ratingOf(p) },
        { label: 'Kích cỡ', render: (p) => sizesOf(p) },
        { label: 'Tồn kho', render: (p) => (p ? `${productStock(p, pickPurchasableVariant(p))}` : 'Đang cập nhật') },
    ];

    return (
        <div className={cx('wrapper')}>
            {notice && <div className={cx('notice', notice.type === 'error' && 'notice-error')}>{notice.message}</div>}
            <header><Header /></header>
            <div><Banner /></div>
            <main className={cx('inner')}>
                <div className={cx('heading')}>
                    <h1>So sánh sản phẩm ({compareItems.length})</h1>
                    <button type="button" className={cx('clear-btn')} onClick={clearCompare}>
                        Xóa tất cả
                    </button>
                </div>

                <div className={cx('table-scroll')}>
                    <table className={cx('compare-table')}>
                        <thead>
                            <tr>
                                <th className={cx('row-label')}></th>
                                {compareItems.map((item) => {
                                    const product = details[item.id];
                                    return (
                                        <th key={item.id} className={cx('product-col')}>
                                            <button
                                                type="button"
                                                className={cx('remove-col')}
                                                onClick={() => removeFromCompare(item.id)}
                                                aria-label="Bỏ khỏi so sánh"
                                            >
                                                <X size={16} />
                                            </button>
                                            <Link to={`/prodetail/${item.id}`} className={cx('col-image')}>
                                                <img
                                                    src={resolveImageUrl(product?.img || item.img)}
                                                    alt={titleOf(product || item)}
                                                    onError={handleImageFallback}
                                                />
                                            </Link>
                                            <Link to={`/prodetail/${item.id}`} className={cx('col-name')}>
                                                {titleOf(product || item)}
                                            </Link>
                                        </th>
                                    );
                                })}
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row) => (
                                <tr key={row.label}>
                                    <td className={cx('row-label')}>{row.label}</td>
                                    {compareItems.map((item) => (
                                        <td key={item.id} className={cx('cell')}>
                                            {loading ? '...' : row.render(details[item.id], item)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                            <tr>
                                <td className={cx('row-label')}></td>
                                {compareItems.map((item) => {
                                    const product = details[item.id];
                                    return (
                                        <td key={item.id} className={cx('cell')}>
                                            <button
                                                type="button"
                                                className={cx('add-cart-btn')}
                                                disabled={loading || !product}
                                                onClick={() => product && handleAddToCart(product)}
                                            >
                                                <ShoppingCart size={15} />
                                                Thêm vào giỏ
                                            </button>
                                        </td>
                                    );
                                })}
                            </tr>
                        </tbody>
                    </table>
                </div>

                <button type="button" className={cx('back-btn')} onClick={() => navigate('/category')}>
                    Tiếp tục mua sắm
                </button>
            </main>
            <footer><Footer /></footer>
        </div>
    );
}

export default ProductComparison;
