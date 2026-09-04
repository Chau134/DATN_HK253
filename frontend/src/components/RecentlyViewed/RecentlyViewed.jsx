import React from 'react';
import classNames from 'classnames/bind';
import { Link } from 'react-router-dom';
import { titleOf } from '../../utils/productDisplay';
import { History, X } from 'lucide-react';
import { useRecentlyViewed } from '../../utils/useRecentlyViewed';
import { clearRecentlyViewed } from '../../utils/recentlyViewed';
import { formatVndFromDb } from '../../utils/price';
import { handleImageFallback, resolveImageUrl } from '../../utils/image';
import styles from './RecentlyViewed.module.scss';

const cx = classNames.bind(styles);

function RecentlyViewed({ excludeId, title = 'Đã xem gần đây' }) {
    const items = useRecentlyViewed().filter((item) => String(item.id) !== String(excludeId));

    if (!items.length) return null;

    return (
        <section className={cx('wrapper')}>
            <div className={cx('header')}>
                <span className={cx('title')}>
                    <History size={18} />
                    {title}
                </span>
                <button type="button" className={cx('clear')} onClick={clearRecentlyViewed}>
                    <X size={14} />
                    Xóa lịch sử
                </button>
            </div>

            <div className={cx('track')}>
                {items.map((item) => (
                    <Link key={item.id} to={`/prodetail/${item.id}`} className={cx('card')}>
                        <div className={cx('image')}>
                            <img
                                src={resolveImageUrl(item.img)}
                                alt={titleOf(item)}
                                onError={handleImageFallback}
                            />
                        </div>
                        <p className={cx('name')}>{titleOf(item)}</p>
                        <span className={cx('price')}>{formatVndFromDb(item.priceNew)}</span>
                    </Link>
                ))}
            </div>
        </section>
    );
}

export default RecentlyViewed;
