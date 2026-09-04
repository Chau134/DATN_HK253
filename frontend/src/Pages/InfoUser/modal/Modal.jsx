import React, { useEffect, useState } from 'react';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import request, { getApiError } from '../../../config/Connect';
import { toast, ToastContainer } from 'react-toastify';

const SETUP_STEP = {
    REQUEST: 'request',
    OTP: 'otp',
    PASSWORD: 'password',
};

const ERROR_MESSAGES = {
    password_login_not_enabled: 'Tai khoan nay chua co mat khau local. Vui long tao mat khau truoc.',
    password_login_already_enabled: 'Tai khoan nay da co mat khau local.',
    invalid_current_password: 'Mat khau hien tai khong dung.',
    invalid_otp: 'Ma OTP khong chinh xac.',
    otp_expired: 'Ma OTP da het han. Vui long gui lai ma moi.',
    otp_attempts_exceeded: 'Ban da nhap sai OTP qua so lan cho phep.',
    invalid_reset_token: 'Phien tao mat khau khong hop le.',
    reset_token_expired: 'Phien tao mat khau da het han. Vui long thuc hien lai.',
    password_confirmation_mismatch: 'Mat khau xac nhan khong khop.',
    otp_email_send_failed: 'Khong the gui email OTP. Vui long thu lai sau.',
    email_service_unavailable: 'Dich vu gui email chua duoc cau hinh.',
};

function apiErrorMessage(error, fallback) {
    const code = error?.response?.data?.error || error?.response?.data?.message;
    return ERROR_MESSAGES[code] || getApiError(error, fallback);
}

export function ChangePassword({ show, setShow, email, passwordLoginEnabled = true, onPasswordChanged }) {
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [setupStep, setSetupStep] = useState(SETUP_STEP.REQUEST);
    const [otp, setOtp] = useState('');
    const [resetToken, setResetToken] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const isSetupMode = !passwordLoginEnabled;

    useEffect(() => {
        if (!show) return;
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setOtp('');
        setResetToken('');
        setSetupStep(SETUP_STEP.REQUEST);
    }, [show, passwordLoginEnabled]);

    const handleClose = () => {
        if (submitting) return;
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setOtp('');
        setResetToken('');
        setSetupStep(SETUP_STEP.REQUEST);
        setShow(false);
    };

    const handleChangePassword = async (e) => {
        e.preventDefault();

        if (!currentPassword || !newPassword || !confirmPassword) {
            toast.error('Vui lòng điền đầy đủ các thông tin.');
            return;
        }

        if (newPassword.length < 8) {
            toast.error('Mật khẩu mới phải có ít nhất 8 ký tự.');
            return;
        }

        if (newPassword !== confirmPassword) {
            toast.error('Mật khẩu mới và xác nhận mật khẩu không khớp.');
            return;
        }

        try {
            setSubmitting(true);
            await request.post('/api/me/change-password', {
                current_password: currentPassword,
                new_password: newPassword,
            });
            toast.success('Đổi mật khẩu thành công!');
            setTimeout(() => {
                handleClose();
            }, 1000);
        } catch (error) {
            toast.error(getApiError(error, 'Đổi mật khẩu thất bại'));
        } finally {
            setSubmitting(false);
        }
    };

    const requestSetupOtp = async (event) => {
        event?.preventDefault();
        if (submitting) return;
        if (!email) {
            toast.error('Tai khoan chua co email de gui OTP.');
            return;
        }

        try {
            setSubmitting(true);
            await request.post('/api/auth/password-reset/request', { email });
            toast.success('Ma OTP da duoc gui den email cua ban.');
            setSetupStep(SETUP_STEP.OTP);
        } catch (error) {
            toast.error(apiErrorMessage(error, 'Khong the gui OTP.'));
        } finally {
            setSubmitting(false);
        }
    };

    const verifySetupOtp = async (event) => {
        event.preventDefault();
        if (submitting) return;
        if (!/^\d{6}$/.test(otp.trim())) {
            toast.error('Ma OTP gom 6 chu so.');
            return;
        }

        try {
            setSubmitting(true);
            const response = await request.post('/api/auth/password-reset/verify', {
                email,
                otp: otp.trim(),
            });
            setResetToken(response.data?.reset_token || '');
            toast.success('OTP hop le. Vui long tao mat khau.');
            setSetupStep(SETUP_STEP.PASSWORD);
        } catch (error) {
            toast.error(apiErrorMessage(error, 'Xac thuc OTP that bai.'));
        } finally {
            setSubmitting(false);
        }
    };

    const createPassword = async (event) => {
        event.preventDefault();
        if (submitting) return;
        if (newPassword.length < 8) {
            toast.error('Mat khau moi phai co it nhat 8 ky tu.');
            return;
        }
        if (newPassword !== confirmPassword) {
            toast.error('Mat khau xac nhan khong khop.');
            return;
        }

        try {
            setSubmitting(true);
            await request.post('/api/me/create-password', {
                reset_token: resetToken,
                new_password: newPassword,
                confirm_password: confirmPassword,
            });
            await onPasswordChanged?.();
            toast.success('Tao mat khau thanh cong.');
            setTimeout(() => {
                handleClose();
            }, 900);
        } catch (error) {
            toast.error(apiErrorMessage(error, 'Tao mat khau that bai.'));
        } finally {
            setSubmitting(false);
        }
    };

    if (isSetupMode) {
        return (
            <Modal show={show} onHide={handleClose} backdrop={submitting ? 'static' : true} keyboard={!submitting}>
                <ToastContainer />
                {setupStep === SETUP_STEP.REQUEST && (
                    <form onSubmit={requestSetupOtp}>
                        <Modal.Header closeButton={!submitting}>
                            <Modal.Title>Tạo Mật Khẩu</Modal.Title>
                        </Modal.Header>
                        <Modal.Body>
                            <p style={{ marginBottom: 16, color: '#475569', fontWeight: 600 }}>
                                Tài khoản Google này chưa có mật khẩu local. OTP sẽ được gửi đến {email}.
                            </p>
                        </Modal.Body>
                        <Modal.Footer>
                            <Button variant="secondary" onClick={handleClose} disabled={submitting}>
                                Đóng
                            </Button>
                            <Button type="submit" variant="primary" disabled={submitting} style={{ backgroundColor: '#0f766e', borderColor: '#0f766e' }}>
                                {submitting ? 'Đang gửi...' : 'Gửi OTP'}
                            </Button>
                        </Modal.Footer>
                    </form>
                )}

                {setupStep === SETUP_STEP.OTP && (
                    <form onSubmit={verifySetupOtp}>
                        <Modal.Header closeButton={!submitting}>
                            <Modal.Title>Xác Thực OTP</Modal.Title>
                        </Modal.Header>
                        <Modal.Body>
                            <div className="mb-3">
                                <label className="form-label" style={{ fontWeight: '600', color: '#334155' }}>Mã OTP</label>
                                <input
                                    inputMode="numeric"
                                    maxLength={6}
                                    className="form-control"
                                    value={otp}
                                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                    disabled={submitting}
                                    required
                                />
                            </div>
                        </Modal.Body>
                        <Modal.Footer>
                            <Button variant="secondary" type="button" onClick={requestSetupOtp} disabled={submitting}>
                                Gửi lại OTP
                            </Button>
                            <Button type="submit" variant="primary" disabled={submitting} style={{ backgroundColor: '#0f766e', borderColor: '#0f766e' }}>
                                {submitting ? 'Đang kiểm tra...' : 'Xác thực'}
                            </Button>
                        </Modal.Footer>
                    </form>
                )}

                {setupStep === SETUP_STEP.PASSWORD && (
                    <form onSubmit={createPassword}>
                        <Modal.Header closeButton={!submitting}>
                            <Modal.Title>Đặt Mật Khẩu</Modal.Title>
                        </Modal.Header>
                        <Modal.Body>
                            <div className="mb-3">
                                <label className="form-label" style={{ fontWeight: '600', color: '#334155' }}>Mật Khẩu Mới</label>
                                <input
                                    type="password"
                                    className="form-control"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    disabled={submitting}
                                    required
                                />
                            </div>
                            <div className="mb-3">
                                <label className="form-label" style={{ fontWeight: '600', color: '#334155' }}>Xác Nhận Mật Khẩu Mới</label>
                                <input
                                    type="password"
                                    className="form-control"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    disabled={submitting}
                                    required
                                />
                            </div>
                        </Modal.Body>
                        <Modal.Footer>
                            <Button variant="secondary" onClick={handleClose} disabled={submitting}>
                                Đóng
                            </Button>
                            <Button type="submit" variant="primary" disabled={submitting} style={{ backgroundColor: '#0f766e', borderColor: '#0f766e' }}>
                                {submitting ? 'Đang lưu...' : 'Tạo mật khẩu'}
                            </Button>
                        </Modal.Footer>
                    </form>
                )}
            </Modal>
        );
    }

    return (
        <Modal show={show} onHide={handleClose} backdrop={submitting ? 'static' : true} keyboard={!submitting}>
            <ToastContainer />
            <form onSubmit={handleChangePassword}>
                <Modal.Header closeButton={!submitting}>
                    <Modal.Title>Thay Đổi Mật Khẩu</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <div className="mb-3">
                        <label className="form-label" style={{ fontWeight: '600', color: '#334155' }}>Mật Khẩu Hiện Tại</label>
                        <input
                            type="password"
                            className="form-control"
                            value={currentPassword}
                            onChange={(e) => setCurrentPassword(e.target.value)}
                            disabled={submitting}
                            required
                        />
                    </div>
                    <div className="mb-3">
                        <label className="form-label" style={{ fontWeight: '600', color: '#334155' }}>Mật Khẩu Mới</label>
                        <input
                            type="password"
                            className="form-control"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            disabled={submitting}
                            required
                        />
                    </div>
                    <div className="mb-3">
                        <label className="form-label" style={{ fontWeight: '600', color: '#334155' }}>Xác Nhận Mật Khẩu Mới</label>
                        <input
                            type="password"
                            className="form-control"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            disabled={submitting}
                            required
                        />
                    </div>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleClose} disabled={submitting}>
                        Đóng
                    </Button>
                    <Button type="submit" variant="primary" disabled={submitting} style={{ backgroundColor: '#0f766e', borderColor: '#0f766e' }}>
                        {submitting ? 'Đang lưu...' : 'Lưu Lại'}
                    </Button>
                </Modal.Footer>
            </form>
        </Modal>
    );
}

export default function EditInfo({ showModalEdit, setShowModalEdit }) {
    const handleClose = () => setShowModalEdit(false);

    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState(Number);

    const handleEditProfile = async () => {
        toast.error('Spring Boot hiện chưa có endpoint cập nhật hồ sơ từ client.');
    };

    return (
        <div>
            <Modal show={showModalEdit} onHide={handleClose}>
                <ToastContainer />
                <Modal.Header closeButton>
                    <Modal.Title>Chỉnh Sửa Thông Tin</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <div className="input-group mb-3">
                        <input
                            type="text"
                            className="form-control"
                            placeholder="Email"
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>

                    <div className="input-group mb-3">
                        <input
                            type="text"
                            className="form-control"
                            placeholder="Số Điện Thoại"
                            onChange={(e) => setPhone(e.target.value)}
                        />
                    </div>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={handleClose}>
                        Đóng
                    </Button>
                    <Button variant="primary" onClick={handleEditProfile}>
                        Lưu Lại
                    </Button>
                </Modal.Footer>
            </Modal>
        </div>
    );
}
