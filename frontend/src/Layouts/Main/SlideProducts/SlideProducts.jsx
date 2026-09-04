import React from 'react';
import classNames from 'classnames/bind';
import styles from './SlideProducts.module.scss';
import SlickSlider from 'react-slick';

import latest1 from './img/0.webp';
import latest2 from './img/1.jpg';
import latest3 from './img/3.webp';
import latest4 from './img/4.webp';

const cx = classNames.bind(styles);
const Slider = SlickSlider.default ?? SlickSlider;

function SlideProducts() {
    const checkScreen = window.screen.width;

    const settings = {
        className: 'center',
        infinite: true,
        centerPadding: '60px',
        slidesToShow: checkScreen < 400 ? 1 : 4,
        swipeToSlide: true,
        autoplay: true,
        speed: 100,
        cssEase: 'linear',
    };
    return (
        <div className={cx('wrapper')}>
            <header className={cx('header-slide')}>
                <h3 >Sản Phẩm Nổi Bật</h3>
            </header>

            <div className={cx('slider-container')}>
                <Slider {...settings}>
                    <div>
                        <img src={latest1} alt="..." style={{ width: '300px', height: '300px', objectFit: 'cover' }}/>
                    </div>
                    <div>
                        <img src={latest2} alt="..." style={{ width: '300px', height: '300px', objectFit: 'cover' }}/>
                    </div>
                    <div>
                        <img src={latest3} alt="..." style={{ width: '300px', height: '300px', objectFit: 'cover' }}/>
                    </div>
                    <div>
                        <img src={latest4} alt="..." style={{ width: '300px', height: '300px', objectFit: 'cover' }}/>
                    </div>
                </Slider>
            </div>
        </div>
    );
}

export default SlideProducts;
