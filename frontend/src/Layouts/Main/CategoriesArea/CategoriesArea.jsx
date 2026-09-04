import React from 'react';
import classNames from 'classnames/bind';
import styles from './CategoriesArea.module.scss';

import services1 from './img/services1.png';
import services2 from './img/services2.png';
import services3 from './img/services3.png';
import services4 from './img/services4.png';

const cx = classNames.bind(styles);

function CategoriesArea() {
    const services = [
        {
            img: services1,
            en: {
                title: 'Quick & Free Shipping',
                desc: 'Enjoy free shipping for orders over $500',
            },
            vi: {
                title: 'Giao hàng nhanh & miễn phí',
                desc: 'Miễn phí vận chuyển cho tất cả đơn hàng trên 500.000đ',
            },
        },
        {
            img: services2,
            en: {
                title: 'Safe Payment',
                desc: 'Pay securely with multiple options',
            },
            vi: {
                title: 'Thanh toán an toàn',
                desc: 'Nhiều phương thức thanh toán an toàn',
            },
        },
        {
            img: services3,
            en: {
                title: 'Refund Guaranteee',
                desc: '30-day hassle-free refund',
            },
            vi: {
                title: 'Đảm bảo hoàn tiền',
                desc: 'Hoàn tiền dễ dàng trong vòng 30 ngày',
            },
        },
        {
            img: services4,
            en: {
                title: '24/7 Support',
                desc: 'We’re here to help anytime',
            },
            vi: {
                title: 'Hỗ trợ 24/7',
                desc: 'Luôn sẵn sàng hỗ trợ khách hàng bất cứ lúc nào',
            },
        },
    ];

    return (
        <div className={cx('wrapper')}>
            {services.map((service, index) => (
                <div className={cx('row-1')} key={index}>
                    <img src={service.img} alt={service.en.title} />
                    <div className={cx('title-container')}>
                        <h5 className={cx('en-title')}>{service.en.title}</h5>
                        <h5 className={cx('vi-title')}>{service.vi.title}</h5>
                    </div>
                    <div className={cx('desc-container')}>
                        <p className={cx('en-desc')}>{service.en.desc}</p>
                        <p className={cx('vi-desc')}>{service.vi.desc}</p>
                    </div>
                </div>
            ))}
        </div>
    );
}

export default CategoriesArea;
