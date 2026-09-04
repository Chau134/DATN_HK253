import React, { useState } from 'react';
import classNames from 'classnames/bind';
import styles from './SlideBar.module.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faBlog, faCartPlus, faFile, faHome, faUser, faSignOutAlt, faGift } from '@fortawesome/free-solid-svg-icons';
import { useSelector, useDispatch } from 'react-redux';
import { logout } from '../../../../redux/authSlice';
import { useNavigate } from 'react-router-dom';
import request from '../../../../config/Connect';



const cx = classNames.bind(styles);

function SlideBar({ setActiveList }) {
    const [checkType, setCheckType] = useState(0);
    const { role, refreshToken } = useSelector((state) => state.auth); // lấy role từ Redux
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const handleActiveList = (data, type) => {
        setCheckType(type);
        setActiveList(data);
    };

    const handleLogout = async () => {
        try {
            if (refreshToken) {
                await request.post('/api/auth/logout', { refresh_token: refreshToken }).catch(() => null);
            }
            dispatch(logout());               // reset role Redux
            window.location.href = '/';       // redirect to home and reload
        } catch (error) {
            console.error('Lỗi logout:', error);
        }
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('controller')}>
                <ul>
                    <li id={cx(checkType === 0 ? 'active' : '')} onClick={() => handleActiveList('dash', 0)}>
                        <FontAwesomeIcon id={cx('icons')} icon={faHome} />
                        <h5>Trang Chủ</h5>
                    </li>

                    {role === 'admin' && (
                        <li id={cx(checkType === 1 ? 'active' : '')} onClick={() => handleActiveList('order', 1)}>
                            <FontAwesomeIcon id={cx('icons')} icon={faFile} />
                            <h5>Đơn Hàng</h5>
                        </li>
                    )}

                    {role === 'admin' && (
                        <>
                            <li id={cx(checkType === 2 ? 'active' : '')} onClick={() => handleActiveList('product', 2)}>
                                <FontAwesomeIcon id={cx('icons')} icon={faCartPlus} />
                                <h5>Sản Phẩm</h5>
                            </li>

                            <li id={cx(checkType === 3 ? 'active' : '')} onClick={() => handleActiveList('customer', 3)}>
                                <FontAwesomeIcon id={cx('icons')} icon={faUser} />
                                <h5>Người Dùng</h5>
                            </li>
                        </>
                    )}

                    {role === 'admin' && (
                        <li id={cx(checkType === 5 ? 'active' : '')} onClick={() => handleActiveList('blog', 5)}>
                            <FontAwesomeIcon id={cx('icons')} icon={faBlog} />
                            <h5>Bài Viết</h5>
                        </li>
                    )}

                    {role === 'admin' && (
                        <li id={cx(checkType === 6 ? 'active' : '')} onClick={() => handleActiveList('promotion', 6)}>
                            <FontAwesomeIcon id={cx('icons')} icon={faGift} />
                            <h5>Khuyến Mãi</h5>
                        </li>
                    )}

                    {role === 'admin' && (
                        <li id={cx(checkType === 7 ? 'active' : '')} onClick={() => handleActiveList('coupon', 7)}>
                            <FontAwesomeIcon id={cx('icons')} icon={faGift} />
                            <h5>Mã Giảm Giá</h5>
                        </li>
                    )}

                    {/* Nút Logout */}
                    {role === 'admin' && (
                        <li id={cx('logout')} onClick={handleLogout} style={{  cursor: 'pointer' }}>
                            <FontAwesomeIcon id={cx('icons')} icon={faSignOutAlt} />
                            <h5>Đăng Xuất</h5>
                        </li>
                    )}
                </ul>
            </div>
        </div>
    );
}

export default SlideBar;
