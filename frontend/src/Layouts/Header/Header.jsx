
import React, { useState, useRef, useEffect } from 'react';
import classNames from 'classnames/bind';
import styles from './Header.module.scss';
import Logo from './img/MC1.jpg';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faUser } from '@fortawesome/free-regular-svg-icons';
import { faBars, faCamera, faCartPlus, faSignOutAlt, faClipboardList, faSearch, faHeart, faBell, faXmark } from '@fortawesome/free-solid-svg-icons';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { logout } from '../../redux/authSlice';
import { setCart } from '../../redux/actions';
import request from '../../config/Connect';
import { fetchDefaultWishlist } from '../../api/wishlistApi';
import { imagePayloadFromFile } from '../../utils/aiImagePayload';

const cx = classNames.bind(styles);

function Header() {
    const navigate = useNavigate();
    const location = useLocation();
    const dispatch = useDispatch();

    const { role, refreshToken } = useSelector(state => state.auth); // Lấy role từ Redux
    const cartItems = useSelector(state => state.cart);
    const [showUserMenu, setShowUserMenu] = useState(false);
    const userMenuRef = useRef(null);
    const [userData, setUserData] = useState(null);
    const [keyword, setKeyword] = useState('');
    const [searchImage, setSearchImage] = useState(null);
    const [searchImageError, setSearchImageError] = useState('');
    const [preparingImage, setPreparingImage] = useState(false);
    const searchImageInputRef = useRef(null);
    const [wishlistCount, setWishlistCount] = useState(0);

    // Notification State
    const [showNotifMenu, setShowNotifMenu] = useState(false);
    const [showMobileMenu, setShowMobileMenu] = useState(false);
    const notifMenuRef = useRef(null);
    const [notifications, setNotifications] = useState([]);
    const [viewArchive, setViewArchive] = useState(false);
    const unreadCount = notifications.filter(n => !n.read).length;

    const displayName = userData?.display_name || userData?.displayName || userData?.full_name || userData?.fullName || userData?.email || '';

    // Load notifications from local storage
    const loadNotifications = () => {
        try {
            const list = JSON.parse(localStorage.getItem('mystery_closet_notifications') || '[]');
            setNotifications(list);
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        loadNotifications();
        window.addEventListener('notifications:changed', loadNotifications);
        return () => window.removeEventListener('notifications:changed', loadNotifications);
    }, []);

    const handleToggleNotifMenu = () => {
        setShowNotifMenu(!showNotifMenu);
        if (showNotifMenu) {
            setViewArchive(false);
        }
    };

    const handleMarkAsRead = (id) => {
        const updated = notifications.map(n => n.id === id ? { ...n, read: true } : n);
        setNotifications(updated);
        localStorage.setItem('mystery_closet_notifications', JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent('notifications:changed'));
    };

    const handleMarkAllAsRead = () => {
        const updated = notifications.map(n => ({ ...n, read: true }));
        setNotifications(updated);
        localStorage.setItem('mystery_closet_notifications', JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent('notifications:changed'));
    };

    const handleDismissNotif = (id, e) => {
        e.stopPropagation();
        const updated = notifications.map(n => n.id === id ? { ...n, dismissed: true, read: true } : n);
        setNotifications(updated);
        localStorage.setItem('mystery_closet_notifications', JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent('notifications:changed'));
    };

    const handleRestoreNotif = (id, e) => {
        e.stopPropagation();
        const updated = notifications.map(n => n.id === id ? { ...n, dismissed: false } : n);
        setNotifications(updated);
        localStorage.setItem('mystery_closet_notifications', JSON.stringify(updated));
        window.dispatchEvent(new CustomEvent('notifications:changed'));
    };

    const handleClearHistory = () => {
        if (window.confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử thông báo không?')) {
            setNotifications([]);
            localStorage.setItem('mystery_closet_notifications', JSON.stringify([]));
            window.dispatchEvent(new CustomEvent('notifications:changed'));
        }
    };

    const handleUseCoupon = (code, e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(code);
        alert(`Đã sao chép mã giảm giá: ${code}. Bạn có thể dán mã này ở phần thanh toán!`);
        setShowNotifMenu(false);
    };

    // Show/hide dropdown user
    const handleShowUserMenu = () => setShowUserMenu(!showUserMenu);

    const handleSearch = (event) => {
        event.preventDefault();
        const searchValue = keyword.trim();

        if (searchImage) {
            navigate('/ai', {
                state: {
                    headerSearch: {
                        query: searchValue,
                        image: searchImage,
                    },
                },
            });
            return;
        }

        if (searchValue) {
            navigate('/ai', {
                state: {
                    headerSearch: {
                        query: searchValue,
                    },
                },
            });
            return;
        }

        navigate('/category');
    };

    const handleSearchImageChange = async (event) => {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;

        setPreparingImage(true);
        setSearchImageError('');
        try {
            const nextImage = await imagePayloadFromFile(file);
            setSearchImage(nextImage);
        } catch (error) {
            setSearchImage(null);
            setSearchImageError(error.message || 'Khong doc duoc anh da chon.');
        } finally {
            setPreparingImage(false);
        }
    };

    const clearSearchImage = () => {
        setSearchImage(null);
        setSearchImageError('');
    };

    // Logout
    const handleLogout = async () => {
        try {
            // Lưu giỏ hàng riêng cho user trước khi logout
            if (role === 'user' && userData && userData.id) {
                localStorage.setItem(`cart_${userData.id}`, JSON.stringify(cartItems));
            }
            // Xóa cart chung (guest cart) để người sau không thấy
            localStorage.setItem('products', JSON.stringify([]));
            localStorage.removeItem('cart_owner');

            if (refreshToken) {
                await request.post('/api/auth/logout', { refresh_token: refreshToken }).catch(() => null);
            }
            dispatch(logout()); // Xóa Redux state
            
            navigate('/', { replace: true });
            window.location.reload(); // Reload để clear state cart trong memory về mảng rỗng (từ localStorage)
        } catch (error) {
            console.error('Lỗi đăng xuất:', error);
        }
    };

    // Click ngoài dropdown
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
                setShowUserMenu(false);
            }
            if (notifMenuRef.current && !notifMenuRef.current.contains(event.target)) {
                setShowNotifMenu(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);


    // Lấy thông tin user nếu role = user
    useEffect(() => {
        if (role === 'user') {
            request.get('/api/me/profile')
                .then(res => {
                    const user = res.data;
                    if (user) {
                        setUserData(user);
                        
                        const currentOwner = localStorage.getItem('cart_owner');
                        
                        // Nếu user khác với người sở hữu cart hiện tại (hoặc chưa có owner)
                        if (currentOwner !== String(user.id)) {
                             // Load giỏ hàng riêng của user
                            const savedCart = localStorage.getItem(`cart_${user.id}`);
                            
                            if (savedCart) {
                                // Nếu có giỏ hàng cũ -> Load nó
                                const parsedCart = JSON.parse(savedCart);
                                dispatch(setCart(parsedCart));
                            } else {
                                // Nếu không có giỏ hàng cũ, và hiện tại đang là Guest (owner=null)
                                // Thì giữ nguyên items của Guest cho User này
                            }
                            
                            // Đánh dấu user hiện tại là owner
                            localStorage.setItem('cart_owner', String(user.id));
                        }
                    }
                })
                .catch(err => console.error(err));
        }
    }, [role, dispatch]);

    useEffect(() => {
        const handleProfileUpdated = (event) => {
            if (event.detail) {
                setUserData(event.detail);
            }
        };
        window.addEventListener('profile:updated', handleProfileUpdated);
        return () => window.removeEventListener('profile:updated', handleProfileUpdated);
    }, []);

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        setKeyword(location.pathname === '/category' ? params.get('keyword') || '' : '');
        setShowMobileMenu(false);
    }, [location.pathname, location.search]);

    // Nếu admin → không render header user
    useEffect(() => {
        if (role !== 'user') {
            setWishlistCount(0);
            return undefined;
        }

        let mounted = true;

        const loadWishlistCount = async () => {
            try {
                const wishlist = await fetchDefaultWishlist();
                if (mounted) setWishlistCount(wishlist?.item_count ?? wishlist?.itemCount ?? wishlist?.items?.length ?? 0);
            } catch {
                if (mounted) setWishlistCount(0);
            }
        };

        const handleWishlistChanged = (event) => {
            if (typeof event.detail?.itemCount === 'number') {
                setWishlistCount(event.detail.itemCount);
            } else {
                loadWishlistCount();
            }
        };

        loadWishlistCount();
        window.addEventListener('wishlist:changed', handleWishlistChanged);

        return () => {
            mounted = false;
            window.removeEventListener('wishlist:changed', handleWishlistChanged);
        };
    }, [role]);


    return (
        <div className={cx('wrapper')}>
            <Link to="/" className={cx('logo-link')}>
                <div className={cx('logo')}>
                    <img src={Logo} alt="Logo" />
                    <h1>Mystery Closet</h1>
                </div>
            </Link>

            <div className={cx('header-content')}>
                <button
                    type='button'
                    className={cx('menu-button')}
                    aria-label='Mo menu dieu huong'
                    aria-expanded={showMobileMenu}
                    title='Menu'
                    onClick={() => setShowMobileMenu((current) => !current)}
                >
                    <FontAwesomeIcon icon={faBars} />
                </button>
                <div className={cx('controller', { 'mobile-open': showMobileMenu })}>
                    <ul>
                        <Link to="/" style={{ textDecoration: 'none', color: '#333' }}>
                            <li>Trang chủ</li>
                        </Link>
                        <Link to="/category" style={{ textDecoration: 'none', color: '#333' }}>
                            <li>Sản Phẩm</li>
                        </Link>
                        <Link to="/tu-van" style={{ textDecoration: 'none', color: '#333' }}>
                            <li>Tư Vấn</li>
                        </Link>
        
                        <Link to="/blog" style={{ textDecoration: 'none', color: '#333' }}>
                            <li>Bài Viết</li>
                        </Link>
                        <Link to="/contact" style={{ textDecoration: 'none', color: '#333' }}>
                            <li>Liên Hệ</li>
                        </Link>

                        {role === 'user' && userData ? (
                            <>
                                <Link to="/cart" style={{ textDecoration: 'none', color: '#333' }}>
                                    <li className={cx('cart-item')}>
                                        <FontAwesomeIcon icon={faCartPlus} />
                                        <span className={cx('cart-text')}>Giỏ hàng</span>
                                    </li>
                                </Link>
                                <Link to="/wishlist" style={{ textDecoration: 'none', color: '#333' }}>
                                    <li className={cx('wishlist-item')} aria-label="Danh sach yeu thich">
                                        <FontAwesomeIcon icon={faHeart} />
                                        <span className={cx('wishlist-count')}>{wishlistCount}</span>
                                    </li>
                                </Link>
                                <li className={cx('notif-item')} ref={notifMenuRef}>
                                    <div className={cx('notif-button')} onClick={handleToggleNotifMenu}>
                                        <FontAwesomeIcon icon={faBell} />
                                        {unreadCount > 0 && <span className={cx('notif-badge')}>{unreadCount}</span>}
                                    </div>

                                    {showNotifMenu && (
                                        <div className={cx('notif-dropdown')}>
                                            <div className={cx('notif-header')}>
                                                <h6>{viewArchive ? 'Lịch Sử Thông Báo' : 'Thông Báo Khuyến Mãi'}</h6>
                                                <div className="d-flex gap-2">
                                                    {viewArchive ? (
                                                        <>
                                                            <button 
                                                                onClick={handleClearHistory} 
                                                                className={cx('mark-all-read')}
                                                                style={{ color: '#b91c1c', border: 'none', background: 'none', cursor: 'pointer', padding: 0 }}
                                                            >
                                                                Xóa lịch sử
                                                            </button>
                                                            <button 
                                                                onClick={() => setViewArchive(false)} 
                                                                className={cx('mark-all-read')}
                                                                style={{ color: '#0066cc', border: 'none', background: 'none', cursor: 'pointer', padding: 0 }}
                                                            >
                                                                Quay lại
                                                            </button>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <button 
                                                                onClick={() => setViewArchive(true)} 
                                                                className={cx('mark-all-read')}
                                                                style={{ color: '#0066cc', border: 'none', background: 'none', cursor: 'pointer', padding: 0 }}
                                                            >
                                                                Lịch sử
                                                            </button>
                                                            {unreadCount > 0 && (
                                                                <button onClick={handleMarkAllAsRead} className={cx('mark-all-read')}>
                                                                    Đọc tất cả
                                                                </button>
                                                            )}
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                            <div className={cx('notif-list')}>
                                                {notifications.filter(n => viewArchive ? true : !n.dismissed).length === 0 ? (
                                                    <div className={cx('notif-empty')}>
                                                        {viewArchive ? 'Lịch sử thông báo trống' : 'Không có thông báo mới'}
                                                    </div>
                                                ) : (
                                                    notifications
                                                        .filter(n => viewArchive ? true : !n.dismissed)
                                                        .map((notif) => (
                                                            <div
                                                                key={notif.id}
                                                                className={cx('notif-card', { unread: !notif.read, dismissed: notif.dismissed })}
                                                                onClick={() => handleMarkAsRead(notif.id)}
                                                            >
                                                                <div className={cx('notif-card-header')}>
                                                                    <span className={cx('notif-title')}>{notif.title}</span>
                                                                    <button
                                                                        className={cx('delete-notif')}
                                                                        title={notif.dismissed ? "Khôi phục thông báo" : "Xóa thông báo"}
                                                                        onClick={(e) => {
                                                                            if (notif.dismissed) {
                                                                                handleRestoreNotif(notif.id, e);
                                                                            } else {
                                                                                handleDismissNotif(notif.id, e);
                                                                            }
                                                                        }}
                                                                    >
                                                                        {notif.dismissed ? '↺' : '×'}
                                                                    </button>
                                                                </div>
                                                                <p className={cx('notif-message')}>{notif.message}</p>
                                                                {notif.coupon_code && (
                                                                    <div className={cx('notif-actions')}>
                                                                        <button
                                                                            className={cx('use-btn')}
                                                                            onClick={(e) => handleUseCoupon(notif.coupon_code, e)}
                                                                        >
                                                                            Sao chép mã: {notif.coupon_code}
                                                                        </button>
                                                                    </div>
                                                                )}
                                                                <span className={cx('notif-time')}>
                                                                    {new Date(notif.created_at).toLocaleDateString('vi-VN')}
                                                                </span>
                                                            </div>
                                                        ))
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </li>
                                 <li className={cx('user-item')} ref={userMenuRef}>
                                     <div className={cx('user-button')} onClick={handleShowUserMenu}>
                                         {userData?.avatar_url || userData?.avatarUrl ? (
                                             <img
                                                 src={userData.avatar_url || userData.avatarUrl}
                                                 alt="Avatar"
                                                 className={cx('user-avatar')}
                                             />
                                         ) : (
                                             <FontAwesomeIcon icon={faUser} />
                                         )}
                                     </div>

                                    {showUserMenu && (
                                        <div className={cx('user-dropdown')}>
                                            <div className={cx('user-info')}>
                                                <p className={cx('user-name')}>Xin chào, {displayName}</p>
                                                <p className={cx('user-email')} title={userData.email}>
                                                    {userData.email}
                                                </p>
                                            </div>
                                            <div className={cx('user-links')}>
                                                <Link to="/info" className={cx('user-link')}>
                                                    <FontAwesomeIcon icon={faUser} />
                                                    <span>Thông tin tài khoản</span>
                                                </Link>
                                                <Link to="/order-history" className={cx('user-link')}>
                                                    <FontAwesomeIcon icon={faClipboardList} />
                                                    <span>Lịch sử đơn hàng</span>
                                                </Link>
                                                <button onClick={handleLogout} className={cx('user-link', 'logout-btn')}>
                                                    <FontAwesomeIcon icon={faSignOutAlt} />
                                                    <span>Đăng xuất</span>
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </li>
                            </>
                        ) : role === 'admin' ? (
                            <>
                                <Link to="/admin" style={{ textDecoration: 'none', color: '#333' }}>
                                    <li>Quản trị</li>
                                </Link>
                                <li style={{ cursor: 'pointer' }} onClick={handleLogout}>
                                    Đăng xuất
                                </li>
                            </>
                        ) : (
                            <>
                                <Link to="/login" style={{ textDecoration: 'none', color: '#333' }}>
                                    <li>Đăng Nhập</li>
                                </Link>
                                <Link to="/register" style={{ textDecoration: 'none', color: '#333' }}>
                                    <li>Đăng Ký</li>
                                </Link>
                            </>
                        )}
                    </ul>
                </div>

                <form className={cx('search-form')} onSubmit={handleSearch}>
                    <input
                        value={keyword}
                        onChange={(event) => setKeyword(event.target.value)}
                        placeholder="Tìm áo, giày, thương hiệu..."
                        aria-label="Tìm kiếm sản phẩm"
                    />
                    <button type="submit" aria-label="Tìm kiếm">
                        <FontAwesomeIcon icon={faSearch} />
                    </button>
                    <button
                        type="button"
                        className={cx('image-search-button', { active: Boolean(searchImage) })}
                        aria-label="Chon anh de tim kiem"
                        title="Tim bang anh"
                        disabled={preparingImage}
                        onClick={() => searchImageInputRef.current?.click()}
                    >
                        <FontAwesomeIcon icon={faCamera} />
                    </button>
                    <input
                        ref={searchImageInputRef}
                        className={cx('image-search-input')}
                        type="file"
                        accept="image/*"
                        onChange={handleSearchImageChange}
                    />
                </form>
                {(searchImage || searchImageError || preparingImage) && (
                    <div className={cx('search-image-status', { error: Boolean(searchImageError) })}>
                        {preparingImage ? (
                            <span>Dang xu ly anh...</span>
                        ) : searchImageError ? (
                            <span>{searchImageError}</span>
                        ) : (
                            <>
                                <span>Da chon anh: {searchImage.filename}</span>
                                <button type="button" aria-label="Bo anh da chon" onClick={clearSearchImage}>
                                    <FontAwesomeIcon icon={faXmark} />
                                </button>
                            </>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

export default Header;
