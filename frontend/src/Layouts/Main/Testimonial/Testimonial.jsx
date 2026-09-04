import React, { useState, useEffect } from 'react';

import classNames from 'classnames/bind';
import styles from './Testimonial.module.scss';
import appleIcon from './img/circle1.png';
import { Slide } from 'react-slideshow-image';
import 'react-slideshow-image/dist/styles.css';
import { fetchRecentReviews } from '../../../api/catalogApi';
import { resolveImageUrl } from '../../../utils/image';
const cx = classNames.bind(styles);

function Testimonial() {
    const [reviews, setReviews] = useState([]);

    useEffect(() => {
        fetchRecentReviews(6)
            .then((data) => {
                setReviews(data);
            })
            .catch((err) => {
                console.error('Failed to fetch recent reviews', err);
            });
    }, []);

    return (
        <div className={cx('wrapper')}>
            <div className={cx('inner')}>
                <h1 className={cx('heading')}>Customer Testimonial</h1>
                <Slide 
                    autoplay={false} 
                    arrows={true}
                    indicators={true} 
                    slidesToScroll={1} 
                    slidesToShow={1}
                >
                    {reviews.length > 0 ? (
                        reviews.map((review, index) => (
                            <div className={cx('slide-item-wrapper')} key={index}>
                                <div className={cx('testimonial-card')}>
                                    {(review.product_name || review.product_image_url) && (
                                        <div className={cx('product-section')}>
                                            <span className={cx('purchased-label')}>Đã mua</span>
                                            <img
                                                src={
                                                    review.product_image_url
                                                        ? resolveImageUrl(review.product_image_url)
                                                        : 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=150&auto=format&fit=crop'
                                                }
                                                alt={review.product_name || 'Sản phẩm'}
                                                className={cx('product-thumbnail')}
                                                onError={(e) => {
                                                    e.currentTarget.onerror = null;
                                                    e.currentTarget.src = 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=150&auto=format&fit=crop';
                                                }}
                                            />
                                            <span className={cx('product-name-text')} title={review.product_name || 'Sản phẩm'}>
                                                {review.product_name || 'Sản phẩm của cửa hàng'}
                                            </span>
                                        </div>
                                    )}
                                    <div className={cx('review-section')}>
                                        <div className={cx('user-profile')}>
                                            <div className={cx('avatar-container')}>
                                                <img
                                                    alt="avatar"
                                                    src={
                                                        review.user?.avatar_url || appleIcon
                                                    }
                                                    onError={(e) => { e.target.onerror = null; e.target.src = appleIcon; }}
                                                />
                                            </div>
                                            <div className={cx('user-info')}>
                                                <h3>{review.user?.full_name || 'Ẩn danh'}</h3>
                                                <div className={cx('rating')}>
                                                    {review.rating}/5 ⭐
                                                </div>
                                            </div>
                                        </div>
                                        <div className={cx('quote-content')}>
                                            {review.content}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className={cx('slide-item-wrapper')}>
                            <div className={cx('testimonial-card')}>
                                <div className={cx('product-section')}>
                                    <span className={cx('purchased-label')}>Đã mua</span>
                                    <img
                                        src="https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=150&auto=format&fit=crop"
                                        alt="Áo T-Shirt Oversize Graphic"
                                        className={cx('product-thumbnail')}
                                    />
                                    <span className={cx('product-name-text')} title="Áo T-Shirt Oversize Graphic">
                                        Áo T-Shirt Oversize Graphic
                                    </span>
                                </div>
                                <div className={cx('review-section')}>
                                    <div className={cx('user-profile')}>
                                        <div className={cx('avatar-container')}>
                                            <img alt="avatar" src={appleIcon} />
                                        </div>
                                        <div className={cx('user-info')}>
                                            <h3>Petey Cruiser</h3>
                                            <div className={cx('rating')}>5/5 ⭐</div>
                                        </div>
                                    </div>
                                    <div className={cx('quote-content')}>
                                        Fashion should celebrate everyone. That’s why we create pieces that fit and flatter every shape. 
                                        Our designs combine comfort, style, and quality to make you feel confident every day.
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </Slide>

            </div>
        </div>
    );
}

export default Testimonial;
