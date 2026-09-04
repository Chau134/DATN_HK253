import React from 'react';
import classNames from 'classnames/bind';
import styles from './Footer.module.scss';
import { Link, useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faFacebookF, faInstagram, faTiktok, faYoutube } from '@fortawesome/free-brands-svg-icons';
import {
    faEnvelope,
    faLocationDot,
    faPhone,
    faClock,
    faShieldHalved,
    faTruck,
    faFileLines,
    faCircleQuestion,
} from '@fortawesome/free-solid-svg-icons';

import BCTLogo from './img/bct.png';
import SSLLogo from './img/ssl.png';
import PaymentLogo from './img/payment.png';

const cx = classNames.bind(styles);

function Footer() {
    const navigate = useNavigate();

    // Hàm để chuyển hướng và cuộn lên đầu trang
    const navigateToPage = (path) => {
        navigate(path);
        window.scrollTo(0, 0);
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('inner')}>
                <div className={cx('footer-content')}>
                    {/* Thông tin pháp lý */}
                    <div className={cx('footer-column')}>
                        <h3 className={cx('footer-title')}>Mystery Closet</h3>
                        <ul className={cx('footer-info')}>
                            <li>Công ty TNHH Thời Trang Mystery Closet</li>
                            <li>Mã số thuế: 0123456789</li>
                            <li>Số ĐKKD: 0123456789 do Sở KH&ĐT TP.HCM cấp ngày 01/01/2025</li>
                            <li>Đã thông báo với Bộ Công Thương</li>
                            <li>Design by MC</li>
                        </ul>
                        <div className={cx('footer-certificates')}>
                            <img src={BCTLogo} alt="Bộ Công Thương" />
                            <img src={SSLLogo} alt="SSL Certificate" />
                        </div>
                    </div>

                    {/* Thông tin liên hệ */}
                    <div className={cx('footer-column')}>
                        <h3 className={cx('footer-title')}>Thông tin liên hệ</h3>
                        <ul className={cx('footer-contact')}>
                            <li>
                                <FontAwesomeIcon icon={faPhone} />
                                <span>Hotline: 1900 1340 (8:00 - 21:00)</span>
                            </li>
                            <li>
                                <FontAwesomeIcon icon={faEnvelope} />
                                <span>Email: cskh@mysterycloset.com</span>
                            </li>
                            <li>
                                <FontAwesomeIcon icon={faLocationDot} />
                                <span>260 Lý Thường Kiệt, Phường 14, Quận 10, TP. HCM, Việt Nam</span>
                            </li>
                            <li>
                                <FontAwesomeIcon icon={faClock} />
                                <span>Giờ làm việc: 8:00 - 21:00 (Tất cả các ngày)</span>
                            </li>
                        </ul>
                    </div>

                    {/* Chính sách quan trọng */}
                    <div className={cx('footer-column')}>
                        <h3 className={cx('footer-title', 'plus')}>Chính sách</h3>
                        <ul className={cx('footer-links')}>
                            <li>
                                <FontAwesomeIcon icon={faShieldHalved} />
                                <a
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        navigateToPage('/chinh-sach-doi-tra');
                                    }}
                                >
                                    Chính sách đổi trả và bảo hành
                                </a>
                            </li>
                            <li>
                                <FontAwesomeIcon icon={faTruck} />
                                <a
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        navigateToPage('/chinh-sach-van-chuyen');
                                    }}
                                >
                                    Chính sách vận chuyển
                                </a>
                            </li>
                            <li>
                                <FontAwesomeIcon icon={faFileLines} />
                                <a
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        navigateToPage('/chinh-sach-bao-mat');
                                    }}
                                >
                                    Chính sách bảo mật
                                </a>
                            </li>
                            <li>
                                <FontAwesomeIcon icon={faFileLines} />
                                <a
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        navigateToPage('/dieu-khoan-su-dung');
                                    }}
                                >
                                    Điều khoản sử dụng
                                </a>
                            </li>
                            <li>
                                <FontAwesomeIcon icon={faCircleQuestion} />
                                <a
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        navigateToPage('/huong-dan-mua-hang');
                                    }}
                                >
                                    Hướng dẫn mua hàng
                                </a>
                            </li>
                        </ul>

                        <h3 className={cx('footer-title', 'social-title')}>Kết nối với chúng tôi</h3>
                        <div className={cx('footer-social')}>
                            <a
                                className={cx('facebook-link')}
                                href="https://www.facebook.com/share/195QJZ9to5/"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <FontAwesomeIcon icon={faFacebookF} />
                            </a>
                            <a
                                className={cx('instagram-link')}
                                href="https://www.instagram.com/le_gnu0?igsh=OXJiYWJzcWs0ZmFw"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <FontAwesomeIcon icon={faInstagram} />
                            </a>
                            <a
                                className={cx('tiktok-link')}
                                href="https://www.tiktok.com/@mchau_134?_r=1&_t=ZS-97CytWfLru9"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <FontAwesomeIcon icon={faTiktok} />
                            </a>
                            <a
                                className={cx('youtube-link')}
                                href="https://www.youtube.com/watch?v=DK23U3sJrYg&list=PLWqZ8_onh-yBGBnC1tCxyC47g4WumzQT1"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <FontAwesomeIcon icon={faYoutube} />
                            </a>
                        </div>
                    </div>
                </div>

                <div className={cx('footer-bottom')}>
                    <div className={cx('payment-methods')}>
                        <p>Phương thức thanh toán</p>
                        <img src={PaymentLogo} alt="Phương thức thanh toán" />
                    </div>
                    <div className={cx('copyright')}>
                        <p>&copy; {new Date().getFullYear()} Mystery Closet. Tất cả các quyền được bảo lưu.</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Footer;
