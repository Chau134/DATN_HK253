import React, { useEffect, useState } from 'react';
import classNames from 'classnames/bind';
import styles from './LoginUser.module.scss';
import Header from '../../Layouts/Header/Header';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import request, { API_BASE_URL, getApiError } from '../../config/Connect';
import { toast, ToastContainer } from 'react-toastify';
import { useDispatch, useSelector } from 'react-redux';
import { loginSuccess } from '../../redux/authSlice';
import { Eye, EyeOff } from 'lucide-react';

const cx = classNames.bind(styles);

const oauth2ErrorMessages = {
    google_oauth_not_configured: 'Google login chưa được cấu hình trên backend.',
    google_email_not_verified: 'Email Google chưa được xác minh.',
    account_not_active: 'Tài khoản của bạn đang bị khóa hoặc chưa kích hoạt.',
    google_email_required: 'Google không trả về email cho tài khoản này.',
    google_login_failed: 'Đăng nhập Google thất bại. Vui lòng thử lại.',
};

function getOAuth2ErrorMessage(error) {
    return oauth2ErrorMessages[error] || 'Đăng nhập Google thất bại. Vui lòng thử lại.';
}

function LoginUser() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();
    const location = useLocation();
    const dispatch = useDispatch();
    const { isAuthenticated, role } = useSelector((state) => state.auth);

    useEffect(() => {
        if (isAuthenticated) {
            navigate(role === 'admin' ? '/admin' : '/', { replace: true });
            return;
        }

        const oauth2Error = location.state?.oauth2Error || new URLSearchParams(location.search).get('oauth2_error');
        if (oauth2Error) {
            toast.error(getOAuth2ErrorMessage(oauth2Error));
            navigate(location.pathname, { replace: true, state: null });
        }
    }, [isAuthenticated, location.pathname, location.search, location.state, navigate, role]);

    const handleLoginUser = async (event) => {
        event?.preventDefault();
        if (loading) return;

        if (!email || !password) {
            toast.error('Vui lòng nhập đầy đủ thông tin');
            return;
        }

        try {
            setLoading(true);
            const res = await request.post('/api/auth/login', { email, password });
            const roles = res.data?.user?.roles || [];

            let role = 'user';
            if (roles.includes('ADMIN')) role = 'admin';

            dispatch(
                loginSuccess({
                    role,
                    user: res.data.user,
                    accessToken: res.data.access_token,
                    refreshToken: res.data.refresh_token,
                }),
            );

            if (role === 'admin') {
                navigate('/admin', { replace: true });
            } else {
                navigate('/', { replace: true });
            }

            toast.success('Đăng nhập thành công!');
        } catch (error) {
            toast.error(getApiError(error, 'Đăng nhập thất bại'));
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleLogin = () => {
        const baseUrl = API_BASE_URL.replace(/\/$/, '');
        window.location.assign(`${baseUrl}/oauth2/authorization/google`);
    };

    return (
        <>
            <ToastContainer />
            <Header />

            <div className={cx('wrapper')}>
                <div className={cx('inner')}>
                    <div className={cx('header-form-login')}>
                        <span>Đăng nhập</span>
                        <p>Nhập thông tin đăng nhập để tiếp tục</p>
                    </div>

                    <form onSubmit={handleLoginUser}>
                        <div className={cx('input-box')}>
                            <div className={cx('form-input')}>
                                <label>Email</label>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="Nhập email"
                                />
                            </div>

                            <div className={cx('form-input')}>
                                <label>Mật khẩu</label>
                                <div className={cx('password-field')}>
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Nhập mật khẩu"
                                    />
                                    <button
                                        type="button"
                                        className={cx('password-toggle')}
                                        onClick={() => setShowPassword((current) => !current)}
                                        aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                                        title={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                                    >
                                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className={cx('forgot-link')}>
                            <Link to="/forgot-password">Quên mật khẩu?</Link>
                        </div>

                        <button className={cx('google-login')} type="button" onClick={handleGoogleLogin}>
                            <svg className={cx('google-icon')} viewBox="0 0 24 24" aria-hidden="true">
                                <path
                                    fill="#4285f4"
                                    d="M23.5 12.3c0-.8-.1-1.5-.2-2.2H12v4.2h6.5c-.3 1.5-1.1 2.7-2.3 3.5v2.9h3.7c2.2-2 3.6-4.9 3.6-8.4z"
                                />
                                <path
                                    fill="#34a853"
                                    d="M12 24c3.2 0 5.9-1.1 7.9-2.9l-3.7-2.9c-1 .7-2.4 1.1-4.2 1.1-3.1 0-5.7-2.1-6.6-4.9H1.6v3c1.9 3.9 5.9 6.6 10.4 6.6z"
                                />
                                <path
                                    fill="#fbbc05"
                                    d="M5.4 14.4c-.2-.7-.4-1.5-.4-2.4s.1-1.7.4-2.4v-3H1.6C.6 8.2 0 10.1 0 12s.6 3.8 1.6 5.4l3.8-3z"
                                />
                                <path
                                    fill="#ea4335"
                                    d="M12 4.7c1.7 0 3.3.6 4.5 1.8l3.3-3.3C17.9 1.2 15.2 0 12 0 7.5 0 3.5 2.7 1.6 6.6l3.8 3C6.3 6.8 8.9 4.7 12 4.7z"
                                />
                            </svg>
                            <span>Đăng nhập với Google</span>
                        </button>

                        <div className={cx('login-footer')}>
                            <p>
                                Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
                            </p>
                            <button type="submit" disabled={loading}>
                                {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </>
    );
}

export default LoginUser;
