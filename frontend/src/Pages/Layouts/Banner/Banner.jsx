import React from 'react';

import classNames from 'classnames/bind';
import styles from './Banner.module.scss';

const cx = classNames.bind(styles);

function Banner() {
    const urlPage = window.location.pathname.slice(1, 9999);
    const pageLabelMap = {
        'tu-van': 'consulting',
    };
    const pageLabel = pageLabelMap[urlPage] || urlPage;
    let result = pageLabel.toUpperCase();
    return (
        <div className={cx('wrapper')}>
            <h1>{result}</h1>
            <span>Home | {pageLabel}</span>
        </div>
    );
}

export default Banner;
