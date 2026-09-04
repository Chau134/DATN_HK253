import React from 'react';
import classNames from 'classnames/bind';
import styles from './Main.module.scss';
import Slide from './Slide/Slide';
import ItemProducts from './ItemProducts/ItemProducts';
import Testimonial from './Testimonial/Testimonial';
import CategoriesArea from './CategoriesArea/CategoriesArea';
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { fetchCatalogProducts, fetchCatalogCategories } from '../../api/catalogApi';
import request from '../../config/Connect';
const cx = classNames.bind(styles);
const defaultTshirts = [
    { img: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop', name: 'Áo T-Shirt Nam Trắng' },
    { img: 'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=500&auto=format&fit=crop', name: 'Áo T-Shirt Đen Classic' },
    { img: 'https://images.unsplash.com/photo-1562157873-818bc0726f68?w=500&auto=format&fit=crop', name: 'Áo T-Shirt Trơn Basic' },
    { img: 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=500&auto=format&fit=crop', name: 'Áo T-Shirt Oversize Graphic' },
];

const defaultShirts = [
    { img: 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=500&auto=format&fit=crop', name: 'Áo Sơ Mi Oxford Classic' },
    { img: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&auto=format&fit=crop', name: 'Áo Sơ Mi Họa Tiết Cá Tính' },
    { img: 'https://images.unsplash.com/photo-1589310243389-96a5483213a8?w=500&auto=format&fit=crop', name: 'Áo Sơ Mi Công Sở Lịch Lãm' },
    { img: 'https://images.unsplash.com/photo-1603252109303-2751441dd157?w=500&auto=format&fit=crop', name: 'Áo Sơ Mi Linen Mùa Hè' },
];

const defaultShoes = [
    { img: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&auto=format&fit=crop', name: 'Giày Thể Thao Nam Nike Red' },
    { img: 'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=500&auto=format&fit=crop', name: 'Giày Sneaker Nữ Pink Pastel' },
    { img: 'https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=500&auto=format&fit=crop', name: 'Sandal Quai Ngang Unisex' },
    { img: 'https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=500&auto=format&fit=crop', name: 'Giày Running Classic Black' },
];

const categoryImages = {
    'apparel': 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800&auto=format&fit=crop',
    'footwear': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=800&auto=format&fit=crop',
    'default': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800&auto=format&fit=crop'
};

const CATEGORY_IDS = {
    tops: 10,
    bottoms: 11,
    dresses: 12,
};

function Main() {
    const [dataProducts, setDataProducts] = useState([]);
    const [tshirtProducts, setTshirtProducts] = useState([]);
    const [shirtProducts, setShirtProducts] = useState([]);
    const [shoeProducts, setShoeProducts] = useState([]);
    const [promotions, setPromotions] = useState([]);
    const [masterCategories, setMasterCategories] = useState([]);

    useEffect(() => {
        const fetchPromotions = async () => {
            try {
                const response = await request.get('/api/promotions');
                setPromotions(response.data || []);
            } catch (error) {
                console.error('Error fetching promotions:', error);
            }
        };
        fetchPromotions();
    }, []);

    useEffect(() => {
        const fetchCategories = async () => {
            try {
                const list = await fetchCatalogCategories();
                const masters = list.filter(cat => cat.level === 'master');
                setMasterCategories(masters);
            } catch (error) {
                console.error('Error fetching categories:', error);
            }
        };
        fetchCategories();
    }, []);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetchCatalogProducts({ page: 0, size: 12, sort: 'newest' });
                setDataProducts(response.items);
            } catch (error) {
                console.error('Error fetching data:', error);
            }

            try {
                const res1 = await fetchCatalogProducts({ page: 0, size: 12, category_id: CATEGORY_IDS.tops });
                const combinedItems = [...(res1.items || [])];

                const uniqueItems = [];
                const seenIds = new Set();
                for (const item of combinedItems) {
                    if (item && item.id && !seenIds.has(item.id)) {
                        seenIds.add(item.id);
                        uniqueItems.push(item);
                    }
                }

                const filtered = uniqueItems.filter((item) => {
                    const title = (item.nameProducts || '').toLowerCase();
                    return !title.includes('t-shirt') && !title.includes('tshirt') && !title.includes('thun');
                });
                setShirtProducts(filtered.slice(0, 12));
            } catch (error) {
                console.error('Error fetching shirts:', error);
            }

            try {
                const response = await fetchCatalogProducts({ page: 0, size: 12, category_id: CATEGORY_IDS.bottoms });
                setTshirtProducts(response.items);
            } catch (error) {
                console.error('Error fetching tshirts:', error);
            }

            try {
                const resShoe = await fetchCatalogProducts({ page: 0, size: 12, category_id: CATEGORY_IDS.dresses });
                setShoeProducts(resShoe.items || []);
            } catch (error) {
                console.error('Error fetching shoes:', error);
            }
        };

        fetchData();
    }, []);

    return (
        <div className={cx('wrapper')}>
            <div className={cx('promotion-marquee')}>
                <div className={cx('marquee-content')}>
                    {promotions.length > 0 ? (
                        <>
                            {promotions.map((promo, idx) => {
                                const discountText = promo.discount_value && Number(promo.discount_value) > 0
                                    ? (promo.discount_type === 'PERCENTAGE'
                                        ? ` - Giảm ngay ${Number(promo.discount_value)}%`
                                        : ` - Giảm ngay ${new Intl.NumberFormat('vi-VN').format(promo.discount_value)}đ`)
                                    : '';
                                return (
                                    <span key={promo.id || idx} className={cx('promo-item')}>
                                        🎁 <strong>{promo.name}</strong>: {promo.description}{discountText} &nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;
                                    </span>
                                );
                            })}
                            {/* Duplicate the items for seamless infinite scroll */}
                            {promotions.map((promo, idx) => {
                                const discountText = promo.discount_value && Number(promo.discount_value) > 0
                                    ? (promo.discount_type === 'PERCENTAGE'
                                        ? ` - Giảm ngay ${Number(promo.discount_value)}%`
                                        : ` - Giảm ngay ${new Intl.NumberFormat('vi-VN').format(promo.discount_value)}đ`)
                                    : '';
                                return (
                                    <span key={`dup-${promo.id || idx}`} className={cx('promo-item')}>
                                        🎁 <strong>{promo.name}</strong>: {promo.description}{discountText} &nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;
                                    </span>
                                );
                            })}
                        </>
                    ) : (
                        <>
                            <span className={cx('promo-item')}>
                                ✨ Chào mừng bạn đến với <strong>Mystery Closet</strong>! Hiện tại cửa hàng chưa có chương trình khuyến mãi mới, hãy theo dõi website thường xuyên để cập nhật thông tin ưu đãi hấp dẫn sắp tới nhé! &nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;
                            </span>
                            {/* Duplicate for seamless infinite scroll */}
                            <span className={cx('promo-item')}>
                                ✨ Chào mừng bạn đến với <strong>Mystery Closet</strong>! Hiện tại cửa hàng chưa có chương trình khuyến mãi mới, hãy theo dõi website thường xuyên để cập nhật thông tin ưu đãi hấp dẫn sắp tới nhé! &nbsp;&nbsp;&nbsp;&nbsp;★&nbsp;&nbsp;&nbsp;&nbsp;
                            </span>
                        </>
                    )}
                </div>
            </div>

            <div className={cx('slide')}>
                <Slide />
            </div>

            <div className={cx('item-products-container')}>
                <h2 className={cx('section-title')}>BẠN ĐANG CẦN TÌM</h2>
                <div className={cx('master-categories-grid')}>
                    {masterCategories.map((cat) => {
                        const img = categoryImages[(cat.name || '').toLowerCase()] || categoryImages['default'];
                        return (
                            <Link to={`/category?category_id=${cat.id}`} key={cat.id} className={cx('category-card')}>
                                <div className={cx('card-bg')} style={{ backgroundImage: `url(${img})` }} />
                                <div className={cx('card-overlay')} />
                                <div className={cx('card-content')}>
                                    <h3>{cat.name_vi || cat.name}</h3>
                                    <span>Khám phá ngay &rarr;</span>
                                </div>
                            </Link>
                        );
                    })}
                </div>
                <div className={cx('explore-button-wrapper')}>
                    <Link to="/category" className={cx('explore-btn')}>
                        KHÁM PHÁ SẢN PHẨM CỦA CHÚNG TÔI
                    </Link>
                </div>
            </div>

            <div className={cx('large-banner-container')}>
                <img
                    className={cx('large-banner')}
                    src="https://res.cloudinary.com/dhtlzqflg/image/upload/q_auto/f_auto/v1780843293/shirts_ugnejm.jpg"
                    alt="Banner Áo Sơ Mi"
                />
            </div>

            <div className={cx('tshirt-section-container')}>
                <div className={cx('tshirt-glass-card')}>
                    <div className={cx('item-products-box')}>
                        <ItemProducts dataProducts={shirtProducts} defaultItems={defaultShirts} />
                    </div>
                    <div className={cx('explore-button-wrapper')}>
                        <Link to={`/category?category_id=${CATEGORY_IDS.tops}`} className={cx('explore-btn')}>
                            XEM TẤT CẢ ÁO
                        </Link>
                    </div>
                </div>
            </div>

            <div className={cx('large-banner-container')}>
                <img
                    className={cx('large-banner')}
                    src="https://res.cloudinary.com/dhtlzqflg/image/upload/q_auto/f_auto/v1780842688/banner1_hx1mgg.png"
                    alt="Banner lớn"
                />
            </div>

            <div className={cx('tshirt-section-container')}>
                <div className={cx('tshirt-glass-card')}>
                    <div className={cx('item-products-box')}>
                        <ItemProducts dataProducts={tshirtProducts} defaultItems={defaultTshirts} />
                    </div>
                    <div className={cx('explore-button-wrapper')}>
                        <Link to={`/category?category_id=${CATEGORY_IDS.bottoms}`} className={cx('explore-btn')}>
                            XEM TẤT CẢ QUẦN & CHÂN VÁY
                        </Link>
                    </div>
                </div>
            </div>

            <div className={cx('large-banner-container')}>
                <img
                    className={cx('large-banner')}
                    src="https://res.cloudinary.com/dhtlzqflg/image/upload/q_auto/f_auto/v1780844082/giay_p0huvy.jpg"
                    alt="Banner Váy Đầm"
                />
            </div>

            <div className={cx('tshirt-section-container')}>
                <div className={cx('tshirt-glass-card')}>
                    <div className={cx('item-products-box')}>
                        <ItemProducts dataProducts={shoeProducts} defaultItems={defaultShoes} />
                    </div>
                    <div className={cx('explore-button-wrapper')}>
                        <Link to={`/category?category_id=${CATEGORY_IDS.dresses}`} className={cx('explore-btn')}>
                            XEM TẤT CẢ VÁY & ĐẦM
                        </Link>
                    </div>
                </div>
            </div>

            <div className={cx('testimonial-section')}>
                <Testimonial />
            </div>

            <div className={cx('categories-area')}>
                <CategoriesArea />
            </div>
        </div>
    );
}

export default Main;
