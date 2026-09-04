import React, { useState } from 'react';
import classNames from 'classnames/bind';
import { Link, useNavigate } from 'react-router-dom';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { Eye, EyeOff } from 'lucide-react';

import Header from '../../Layouts/Header/Header';
import request, { getApiError } from '../../config/Connect';
import styles from './RegisterUser.module.scss';

const cx = classNames.bind(styles);

function RegisterUser() {
    const navigate = useNavigate();
    const [lastName, setLastName] = useState('');
    const [firstName, setFirstName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleRegister = async () => {
        if (loading) return;

        const normalizedLastName = lastName.trim();
        const normalizedFirstName = firstName.trim();
        const normalizedEmail = email.trim();
        const normalizedPhone = phone.trim();
        const fullName = [normalizedLastName, normalizedFirstName].filter(Boolean).join(' ');

        if (!normalizedLastName || !normalizedFirstName || !normalizedEmail || !normalizedPhone || !password || !confirmPassword) {
            toast.error('Vui lòng nhập đầy đủ thông tin');
            return;
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
            toast.error('Email không đúng định dạng');
            return;
        }

        if (!/^[0-9]{10}$/.test(normalizedPhone)) {
            toast.error('Số điện thoại phải gồm 10 chữ số');
            return;
        }

        if (password.length < 8) {
            toast.error('Mật khẩu phải có ít nhất 8 ký tự');
            return;
        }

        if (password !== confirmPassword) {
            toast.error('Mật khẩu xác nhận không trùng khớp');
            return;
        }

        try {
            setLoading(true);
            await request.post('/api/auth/register', {
                full_name: fullName,
                display_name: normalizedFirstName,
                email: normalizedEmail,
                password,
                phone_number: normalizedPhone,
            });
            toast.success('Đăng ký thành công');
            setTimeout(() => navigate('/login'), 1200);
        } catch (error) {
            toast.error(getApiError(error, 'Đăng ký thất bại. Vui lòng thử lại.'));
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (event) => {
        if (event.key === 'Enter') {
            handleRegister();
        }
    };

    return (
        <>
            <ToastContainer />
            <header>
                <Header />
            </header>
            <div className={cx('wrapper')}>
                <div className={cx('inner')}>
                    <div className={cx('header-form-login')}>
                        <span>Đăng ký</span>
                        <p>Tạo tài khoản để mua sắm và theo dõi đơn hàng</p>
                    </div>
                    <div className={cx('input-box')}>
                        <div className={cx('name-row')}>
                            <div className={cx('form-input')}>
                                <label>Họ</label>
                                <input
                                    value={lastName}
                                    placeholder="Nhập họ"
                                    onChange={(event) => setLastName(event.target.value)}
                                    onKeyDown={handleKeyDown}
                                />
                            </div>

                            <div className={cx('form-input')}>
                                <label>Tên</label>
                                <input
                                    value={firstName}
                                    placeholder="Nhập tên"
                                    onChange={(event) => setFirstName(event.target.value)}
                                    onKeyDown={handleKeyDown}
                                />
                            </div>
                        </div>

                        <div className={cx('form-input')}>
                            <label>Email</label>
                            <input
                                type="email"
                                value={email}
                                placeholder="Nhập email"
                                onChange={(event) => setEmail(event.target.value)}
                                onKeyDown={handleKeyDown}
                            />
                        </div>

                        <div className={cx('form-input')}>
                            <label>Số điện thoại</label>
                            <input
                                value={phone}
                                placeholder="Nhập số điện thoại"
                                onChange={(event) => setPhone(event.target.value)}
                                onKeyDown={handleKeyDown}
                            />
                        </div>

                        <div className={cx('form-input')}>
                            <label>Mật khẩu</label>
                            <div className={cx('password-field')}>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    placeholder="Nhập mật khẩu"
                                    onChange={(event) => setPassword(event.target.value)}
                                    onKeyDown={handleKeyDown}
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

                        <div className={cx('form-input')}>
                            <label>Xác nhận mật khẩu</label>
                            <div className={cx('password-field')}>
                                <input
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    value={confirmPassword}
                                    placeholder="Nhập lại mật khẩu"
                                    onChange={(event) => setConfirmPassword(event.target.value)}
                                    onKeyDown={handleKeyDown}
                                />
                                <button
                                    type="button"
                                    className={cx('password-toggle')}
                                    onClick={() => setShowConfirmPassword((current) => !current)}
                                    aria-label={showConfirmPassword ? 'Ẩn mật khẩu xác nhận' : 'Hiện mật khẩu xác nhận'}
                                    title={showConfirmPassword ? 'Ẩn mật khẩu xác nhận' : 'Hiện mật khẩu xác nhận'}
                                >
                                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>
                    </div>
                    <div className={cx('login-footer')}>
                        <p>
                            Đã có tài khoản?
                            <Link className={cx('login-link')} to="/login">
                                Đăng nhập
                            </Link>
                        </p>
                        <button onClick={handleRegister} disabled={loading} className={cx(loading ? 'loading' : '')}>
                            {loading ? 'Đang xử lý...' : 'Đăng ký'}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}

export default RegisterUser;
