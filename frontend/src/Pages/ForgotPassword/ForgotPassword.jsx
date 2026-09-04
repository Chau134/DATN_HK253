import React, { useState } from 'react';
import classNames from 'classnames/bind';
import { useNavigate } from 'react-router-dom';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Header from '../../Layouts/Header/Header';
import request, { getApiError } from '../../config/Connect';
import styles from './ForgotPassword.module.scss';

const cx = classNames.bind(styles);

const STEP = {
    EMAIL: 'email',
    OTP: 'otp',
    PASSWORD: 'password',
};

const ERROR_MESSAGES = {
    email_not_found: 'Email khong ton tai trong he thong.',
    account_not_active: 'Tai khoan nay hien khong hoat dong.',
    invalid_otp: 'Ma OTP khong chinh xac.',
    otp_expired: 'Ma OTP da het han. Vui long gui lai ma moi.',
    otp_attempts_exceeded: 'Ban da nhap sai OTP qua so lan cho phep.',
    invalid_reset_token: 'Phien dat lai mat khau khong hop le.',
    reset_token_expired: 'Phien dat lai mat khau da het han. Vui long thuc hien lai.',
    password_confirmation_mismatch: 'Mat khau xac nhan khong khop.',
    otp_email_send_failed: 'Khong the gui email OTP. Vui long thu lai sau.',
    email_service_unavailable: 'Dich vu gui email chua duoc cau hinh.',
};

function apiErrorMessage(error, fallback) {
    const code = error?.response?.data?.error || error?.response?.data?.message;
    return ERROR_MESSAGES[code] || getApiError(error, fallback);
}

function ForgotPassword() {
    const [step, setStep] = useState(STEP.EMAIL);
    const [email, setEmail] = useState('');
    const [otp, setOtp] = useState('');
    const [resetToken, setResetToken] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    const requestOtp = async (event) => {
        event.preventDefault();
        if (loading) return;
        if (!email.trim()) {
            toast.error('Vui long nhap email da dang ky.');
            return;
        }

        try {
            setLoading(true);
            await request.post('/api/auth/password-reset/request', { email: email.trim() });
            toast.success('Ma OTP da duoc gui den email cua ban.');
            setStep(STEP.OTP);
        } catch (error) {
            toast.error(apiErrorMessage(error, 'Khong the gui OTP.'));
        } finally {
            setLoading(false);
        }
    };

    const verifyOtp = async (event) => {
        event.preventDefault();
        if (loading) return;
        if (!/^\d{6}$/.test(otp.trim())) {
            toast.error('Ma OTP gom 6 chu so.');
            return;
        }

        try {
            setLoading(true);
            const response = await request.post('/api/auth/password-reset/verify', {
                email: email.trim(),
                otp: otp.trim(),
            });
            setResetToken(response.data?.reset_token || '');
            toast.success('OTP hop le. Vui long dat mat khau moi.');
            setStep(STEP.PASSWORD);
        } catch (error) {
            toast.error(apiErrorMessage(error, 'Xac thuc OTP that bai.'));
        } finally {
            setLoading(false);
        }
    };

    const confirmReset = async (event) => {
        event.preventDefault();
        if (loading) return;
        if (newPassword.length < 8) {
            toast.error('Mat khau moi phai co it nhat 8 ky tu.');
            return;
        }
        if (newPassword !== confirmPassword) {
            toast.error('Mat khau xac nhan khong khop.');
            return;
        }

        try {
            setLoading(true);
            await request.post('/api/auth/password-reset/confirm', {
                reset_token: resetToken,
                new_password: newPassword,
                confirm_password: confirmPassword,
            });
            toast.success('Dat lai mat khau thanh cong. Vui long dang nhap lai.');
            setTimeout(() => navigate('/login', { replace: true }), 900);
        } catch (error) {
            toast.error(apiErrorMessage(error, 'Dat lai mat khau that bai.'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <ToastContainer />
            <Header />

            <div className={cx('wrapper')}>
                <main className={cx('main')}>
                    {step === STEP.EMAIL && (
                        <form className={cx('inner')} onSubmit={requestOtp}>
                            <h1>Quen mat khau</h1>
                            <p>Nhap email da dang ky de nhan ma OTP.</p>
                            <label>Email</label>
                            <input
                                type="email"
                                value={email}
                                placeholder="email@example.com"
                                onChange={(event) => setEmail(event.target.value)}
                            />
                            <button type="submit" disabled={loading}>
                                {loading ? 'Dang gui...' : 'Gui OTP'}
                            </button>
                        </form>
                    )}

                    {step === STEP.OTP && (
                        <form className={cx('inner')} onSubmit={verifyOtp}>
                            <h1>Xac thuc OTP</h1>
                            <p>Nhap ma 6 chu so da duoc gui den {email}.</p>
                            <label>Ma OTP</label>
                            <input
                                inputMode="numeric"
                                maxLength={6}
                                value={otp}
                                placeholder="123456"
                                onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
                            />
                            <button type="submit" disabled={loading}>
                                {loading ? 'Dang kiem tra...' : 'Xac thuc OTP'}
                            </button>
                            <button className={cx('secondary')} type="button" disabled={loading} onClick={requestOtp}>
                                Gui lai OTP
                            </button>
                        </form>
                    )}

                    {step === STEP.PASSWORD && (
                        <form className={cx('inner')} onSubmit={confirmReset}>
                            <h1>Dat mat khau moi</h1>
                            <p>Mat khau moi se duoc ma hoa va cap nhat cho tai khoan cua ban.</p>
                            <label>Mat khau moi</label>
                            <input
                                type="password"
                                value={newPassword}
                                placeholder="Toi thieu 8 ky tu"
                                onChange={(event) => setNewPassword(event.target.value)}
                            />
                            <label>Xac nhan mat khau</label>
                            <input
                                type="password"
                                value={confirmPassword}
                                placeholder="Nhap lai mat khau moi"
                                onChange={(event) => setConfirmPassword(event.target.value)}
                            />
                            <button type="submit" disabled={loading}>
                                {loading ? 'Dang cap nhat...' : 'Dat lai mat khau'}
                            </button>
                        </form>
                    )}
                </main>
            </div>
        </>
    );
}

export default ForgotPassword;
