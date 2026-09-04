import React from 'react';
import classNames from 'classnames/bind';
import { Link } from 'react-router-dom';
import { X, GitCompare } from 'lucide-react';
import { useCompare } from '../../utils/useCompare';
import { removeFromCompare, clearCompare } from '../../utils/compare';
import { handleImageFallback, resolveImageUrl } from '../../utils/image';
import styles from './CompareBar.module.scss';
import { titleOf } from '../../utils/productDisplay';

const cx = classNames.bind(styles);

function CompareBar() {
    const items = useCompare();

    if (!items.length) return null;

    return (
        <div className={cx('bar')}>
            <div className={cx('inner')}>
                <div className={cx('label')}>
                    <GitCompare size={18} />
                    <span>So sánh ({items.length})</span>
                </div>

                <div className={cx('items')}>
                    {items.map((item) => (
                        <div key={item.id} className={cx('item')}>
                            <img
                                src={resolveImageUrl(item.img)}
                                alt={titleOf(item)}
                                onError={handleImageFallback}
                            />
                            <button
                                type="button"
                                className={cx('remove')}
                                onClick={() => removeFromCompare(item.id)}
                                aria-label="Bỏ khỏi so sánh"
                            >
                                <X size={12} />
                            </button>
                        </div>
                    ))}
                </div>

                <div className={cx('actions')}>
                    <button type="button" className={cx('clear')} onClick={clearCompare}>
                        Xóa
                    </button>
                    <Link to="/compare" className={cx('compare-btn')}>
                        So sánh ngay
                    </Link>
                </div>
            </div>
        </div>
    );
}

export default CompareBar;
