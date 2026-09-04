import React from 'react';
import classNames from 'classnames/bind';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { X } from 'lucide-react';
import { formatVndFromDb } from '../../utils/price';
import styles from './FilterSidebar.module.scss';

const cx = classNames.bind(styles);

function FilterSidebar({
    brands = [],
    selectedBrand = '',
    onSelectBrand,
    priceRange,
    priceBounds,
    onPriceChange,
    onPriceCommit,
    hasActiveFilters = false,
    onClearAll,
}) {
    return (
        <div className={cx('wrapper')}>
            <div className={cx('header')}>
                <h3>Bộ lọc</h3>
                {hasActiveFilters && (
                    <button type="button" className={cx('clear-all')} onClick={onClearAll}>
                        Xóa tất cả
                    </button>
                )}
            </div>

            {hasActiveFilters && (
                <div className={cx('active-chips')}>
                    {selectedBrand && (
                        <span className={cx('chip')}>
                            {selectedBrand}
                            <button type="button" onClick={() => onSelectBrand(selectedBrand)} aria-label={`Bỏ lọc ${selectedBrand}`}>
                                <X size={12} />
                            </button>
                        </span>
                    )}
                    {(priceRange[0] > priceBounds[0] || priceRange[1] < priceBounds[1]) && (
                        <span className={cx('chip')}>
                            {formatVndFromDb(priceRange[0])} - {formatVndFromDb(priceRange[1])}
                        </span>
                    )}
                </div>
            )}

            <div className={cx('section')}>
                <span className={cx('section-title')}>Khoảng giá</span>
                <div className={cx('price-values')}>
                    <span>{formatVndFromDb(priceRange[0])}</span>
                    <span>{formatVndFromDb(priceRange[1])}</span>
                </div>
                <Slider
                    range
                    min={priceBounds[0]}
                    max={priceBounds[1]}
                    step={50000}
                    value={priceRange}
                    onChange={onPriceChange}
                    onChangeComplete={onPriceCommit}
                    allowCross={false}
                />
            </div>

            {brands.length > 0 && (
                <div className={cx('section')}>
                    <span className={cx('section-title')}>Thương hiệu</span>
                    <div className={cx('option-list')}>
                        {brands.map((brand) => (
                            <label key={brand} className={cx('option')}>
                                <input
                                    type="radio"
                                    name="brand-filter"
                                    checked={selectedBrand === brand}
                                    onChange={() => onSelectBrand(brand)}
                                />
                                <span>{brand}</span>
                            </label>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default FilterSidebar;
