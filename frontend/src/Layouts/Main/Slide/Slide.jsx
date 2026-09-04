import React from 'react';
import 'react-slideshow-image/dist/styles.css';

import classNames from 'classnames/bind';
import styles from './Slide.module.scss';

import SlickSlider from 'react-slick';

import imgBanner from './img/b0.jpg';
import imgBanner4 from './img/b0.jpg';
import imgBanner5 from './img/b1.jpg';
import imgBanner2 from './img/b2.jpg';
const cx = classNames.bind(styles);
const Slider = SlickSlider.default ?? SlickSlider;

function SlideWeb() {
    var settings = {
        dots: false,
        infinite: true,
        speed: 500,
        slidesToShow: 1,
        slidesToScroll: 1,
        arrows: false,
        autoplay: true,
    };

    return (
        <div className={cx('slide-container')}>
            <Slider {...settings}>
                
                <div>
                    <img id={cx('test')} src={imgBanner4} />
                </div>
                <div>
                    <img id={cx('test')} src={imgBanner5} />
                </div>
                <div>
                    <img id={cx('test')} src={imgBanner2} />
                </div>
                {/* <div>
                    <img id={cx('test')} src={imgBanner} />
                </div> */}
            </Slider>
        </div>
    );
}

export default SlideWeb;
