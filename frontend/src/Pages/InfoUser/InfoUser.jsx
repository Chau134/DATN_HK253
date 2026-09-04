import React, { useEffect, useMemo, useState } from 'react';
import classNames from 'classnames/bind';
import { CheckCircle, LogOut, MapPin, Pencil, Plus, Save, Trash2, User, Key } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import request, { getApiError } from '../../config/Connect';
import { ChangePassword } from './modal/Modal';
import styles from './InfoUser.module.scss';

const cx = classNames.bind(styles);

const emptyProfile = {
    email: '',
    phone_number: '',
    full_name: '',
    display_name: '',
    first_name: '',
    last_name: '',
    gender: '',
    date_of_birth: '',
    avatar_url: '',
    marketing_opt_in: false,
    password_login_enabled: true,
};

const emptyAddress = {
    address_type: 'SHIPPING',
    recipient_name: '',
    phone_number: '',
    address_line1: '',
    address_line2: '',
    ward: '',
    district: '',
    city: '',
    province: '',
    country_code: 'VN',
    postal_code: '',
    is_default: false,
};

function InfoUser() {
    const navigate = useNavigate();
    const [profile, setProfile] = useState(emptyProfile);
    const [profileForm, setProfileForm] = useState(emptyProfile);
    const [addresses, setAddresses] = useState([]);
    const [addressForm, setAddressForm] = useState(emptyAddress);
    const [editingAddressId, setEditingAddressId] = useState(null);
    const [showAddressForm, setShowAddressForm] = useState(false);
    const [loading, setLoading] = useState(true);
    const [savingProfile, setSavingProfile] = useState(false);
    const [savingAddress, setSavingAddress] = useState(false);
    const [avatarFile, setAvatarFile] = useState(null);
    const [avatarPreview, setAvatarPreview] = useState('');
    const [notice, setNotice] = useState(null);
    const [showChangePass, setShowChangePass] = useState(false);

    const avatarName = useMemo(() => {
        return profile.display_name || profile.full_name || profile.email || 'Customer';
    }, [profile.display_name, profile.email, profile.full_name]);

    const avatarSrc =
        avatarPreview ||
        profile.avatar_url ||
        `https://ui-avatars.com/api/?name=${encodeURIComponent(avatarName)}&background=111827&color=fff`;

    useEffect(() => {
        loadAccount();
    }, []);

    useEffect(() => {
        if (!avatarFile) {
            setAvatarPreview('');
            return undefined;
        }

        const nextPreview = URL.createObjectURL(avatarFile);
        setAvatarPreview(nextPreview);
        return () => URL.revokeObjectURL(nextPreview);
    }, [avatarFile]);

    const loadAccount = async () => {
        try {
            setLoading(true);
            const [profileRes, addressRes] = await Promise.all([
                request.get('/api/me/profile'),
                request.get('/api/me/addresses'),
            ]);
            const nextProfile = normalizeProfile(profileRes.data);
            setProfile(nextProfile);
            setProfileForm(nextProfile);
            setAddresses(addressRes.data || []);
        } catch (error) {
            showNotice('error', getApiError(error, 'Không lấy được thông tin tài khoản'));
            navigate('/login');
        } finally {
            setLoading(false);
        }
    };

    const normalizeProfile = (data) => ({
        ...emptyProfile,
        ...data,
        date_of_birth: data?.date_of_birth || '',
        marketing_opt_in: Boolean(data?.marketing_opt_in),
    });

    const updateProfileField = (field, value) => {
        setProfileForm((current) => ({ ...current, [field]: value }));
    };

    const updateAddressField = (field, value) => {
        setAddressForm((current) => ({ ...current, [field]: value }));
    };

    const showNotice = (type, message) => {
        setNotice({ type, message });
        window.setTimeout(() => {
            setNotice((current) => (current?.message === message ? null : current));
        }, 3500);
    };

    const saveProfile = async (event) => {
        event.preventDefault();
        try {
            setSavingProfile(true);
            const fullName = [profileForm.last_name?.trim(), profileForm.first_name?.trim()].filter(Boolean).join(' ');
            const payload = {
                ...profileForm,
                date_of_birth: profileForm.date_of_birth || null,
                email: profileForm.email?.trim() || '',
                phone_number: profileForm.phone_number?.trim() || null,
                full_name: fullName || null,
                display_name: profileForm.display_name?.trim() || null,
                first_name: profileForm.first_name?.trim() || null,
                last_name: profileForm.last_name?.trim() || null,
                gender: profileForm.gender || null,
            };
            delete payload.avatar_url;
            await request.patch('/api/me/profile', payload);
            const nextProfile = avatarFile ? await uploadSelectedAvatar() : await fetchProfile();
            setProfile(nextProfile);
            setProfileForm(nextProfile);
            window.dispatchEvent(new CustomEvent('profile:updated', { detail: nextProfile }));
            showNotice('success', avatarFile ? 'Đã cập nhật thông tin và ảnh đại diện' : 'Đã cập nhật thông tin tài khoản');
        } catch (error) {
            showNotice('error', getApiError(error, 'Cập nhật thông tin thất bại'));
        } finally {
            setSavingProfile(false);
        }
    };

    const fetchProfile = async () => {
        const profileRes = await request.get('/api/me/profile');
        return normalizeProfile(profileRes.data);
    };

    const uploadSelectedAvatar = async () => {
        const formData = new FormData();
        formData.append('file', avatarFile);
        await request.post('/api/me/avatar', formData);
        const nextProfile = await fetchProfile();
        if (!nextProfile.avatar_url) {
            throw new Error('avatar_url_not_saved');
        }
        setAvatarFile(null);
        return nextProfile;
    };

    const handleDeleteAvatar = async () => {
        if (!window.confirm('Bạn có chắc chắn muốn xóa ảnh đại diện hiện tại không?')) {
            return;
        }
        try {
            setSavingProfile(true);
            const res = await request.delete('/api/me/avatar');
            const nextProfile = normalizeProfile(res.data);
            setProfile(nextProfile);
            setProfileForm(nextProfile);
            window.dispatchEvent(new CustomEvent('profile:updated', { detail: nextProfile }));
            showNotice('success', 'Đã xóa ảnh đại diện');
        } catch (error) {
            showNotice('error', getApiError(error, 'Xóa ảnh đại diện thất bại'));
        } finally {
            setSavingProfile(false);
        }
    };

    const saveAddress = async (event) => {
        event.preventDefault();
        try {
            setSavingAddress(true);
            if (editingAddressId) {
                await request.patch(`/api/me/addresses/${editingAddressId}`, addressForm);
                showNotice('success', 'Đã cập nhật địa chỉ');
            } else {
                await request.post('/api/me/addresses', addressForm);
                showNotice('success', 'Đã thêm địa chỉ');
            }
            resetAddressForm();
            setShowAddressForm(false);
            const res = await request.get('/api/me/addresses');
            setAddresses(res.data || []);
        } catch (error) {
            showNotice('error', getApiError(error, 'Lưu địa chỉ thất bại'));
        } finally {
            setSavingAddress(false);
        }
    };

    const editAddress = (address) => {
        setEditingAddressId(address.id);
        setAddressForm({
            ...emptyAddress,
            ...address,
            country_code: address.country_code || 'VN',
            is_default: Boolean(address.is_default),
        });
        setShowAddressForm(true);
    };

    const deleteAddress = async (addressId) => {
        try {
            await request.delete(`/api/me/addresses/${addressId}`);
            setAddresses((current) => current.filter((item) => item.id !== addressId));
            if (editingAddressId === addressId) {
                resetAddressForm();
            }
            showNotice('success', 'Đã xóa địa chỉ');
        } catch (error) {
            showNotice('error', getApiError(error, 'Xóa địa chỉ thất bại'));
        }
    };

    const resetAddressForm = () => {
        setEditingAddressId(null);
        setAddressForm(emptyAddress);
        setShowAddressForm(false);
    };

    const handleLogout = () => {
        localStorage.removeItem('client_auth');
        navigate('/');
        window.location.reload();
    };

    return (
        <div className={cx('wrapper')}>
            <Header />
            <main className={cx('inner')}>
                {notice && <div className={cx('notice', notice.type)}>{notice.message}</div>}
                <section className={cx('accountHero')}>
                    <div className={cx('avatarWrap')}>
                        <img src={avatarSrc} alt="Avatar" />
                    </div>
                    <div className={cx('identity')}>
                        <span className={cx('eyebrow')}>Tài khoản của tôi</span>
                        <h1>{profile.display_name || profile.full_name || profile.email || 'Khách hàng'}</h1>
                        <p>{profile.email || 'Đang tải thông tin'}</p>
                    </div>
                    <div className={cx('heroActions')}>
                        <button type="button" className={cx('primaryButton')} style={{ marginTop: 0 }} onClick={() => setShowChangePass(true)}>
                            <Key size={18} />
                            {profile.password_login_enabled ? 'Đổi mật khẩu' : 'Tạo mật khẩu'}
                        </button>
                        <button type="button" className={cx('logoutButton')} onClick={handleLogout}>
                            <LogOut size={18} />
                            Đăng xuất
                        </button>
                    </div>
                </section>

                <section className={cx('contentGrid')}>
                    <form className={cx('panel')} onSubmit={saveProfile}>
                        <div className={cx('sectionTitle')}>
                            <User size={20} />
                            <h2>Thông tin cá nhân</h2>
                        </div>

                        <div className={cx('formGrid')}>
                            <label>
                                Tên hiển thị
                                <input
                                    value={profileForm.display_name}
                                    onChange={(e) => updateProfileField('display_name', e.target.value)}
                                    disabled={loading}
                                />
                            </label>
                            <label>
                                Email
                                <input
                                    type="email"
                                    value={profileForm.email}
                                    onChange={(e) => updateProfileField('email', e.target.value)}
                                    disabled={loading}
                                />
                            </label>
                            <label>
                                Tên
                                <input
                                    value={profileForm.first_name || ''}
                                    onChange={(e) => updateProfileField('first_name', e.target.value)}
                                    disabled={loading}
                                />
                            </label>
                            <label>
                                Họ
                                <input
                                    value={profileForm.last_name || ''}
                                    onChange={(e) => updateProfileField('last_name', e.target.value)}
                                    disabled={loading}
                                />
                            </label>
                            <label>
                                Số điện thoại
                                <input
                                    value={profileForm.phone_number || ''}
                                    onChange={(e) => updateProfileField('phone_number', e.target.value)}
                                    disabled={loading}
                                />
                            </label>
                            <label>
                                Giới tính
                                <select
                                    value={profileForm.gender || ''}
                                    onChange={(e) => updateProfileField('gender', e.target.value)}
                                    disabled={loading}
                                >
                                    <option value="">Chưa cập nhật</option>
                                    <option value="FEMALE">Nữ</option>
                                    <option value="MALE">Nam</option>
                                    <option value="OTHER">Khác</option>
                                </select>
                            </label>
                            <label>
                                Ngày sinh
                                <input
                                    type="date"
                                    value={profileForm.date_of_birth || ''}
                                    onChange={(e) => updateProfileField('date_of_birth', e.target.value)}
                                    disabled={loading}
                                />
                            </label>
                             <div className={cx('avatarUpload', 'wide')}>
                                <span>Ảnh đại diện</span>
                                <div className={cx('uploadRow')}>
                                    <input
                                        type="file"
                                        accept="image/png,image/jpeg,image/webp"
                                        onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
                                        disabled={loading || savingProfile}
                                    />
                                    {avatarFile && (
                                        <button
                                            type="button"
                                            className={cx('clearAvatarButton')}
                                            onClick={() => setAvatarFile(null)}
                                        >
                                            Hủy chọn
                                        </button>
                                    )}
                                    {profile.avatar_url && !avatarFile && (
                                        <button
                                            type="button"
                                            className={cx('deleteAvatarButton')}
                                            onClick={handleDeleteAvatar}
                                            disabled={loading || savingProfile}
                                        >
                                            Xóa ảnh
                                        </button>
                                    )}
                                </div>
                                <small>Chấp nhận PNG, JPG, WEBP tối đa 5MB. </small>
                            </div>
                            <label className={cx('toggleRow')}>
                                <input
                                    type="checkbox"
                                    checked={Boolean(profileForm.marketing_opt_in)}
                                    onChange={(e) => updateProfileField('marketing_opt_in', e.target.checked)}
                                    disabled={loading}
                                />
                                Nhận thông tin khuyến mãi
                            </label>
                        </div>

                        <button type="submit" className={cx('primaryButton')} disabled={savingProfile || loading}>
                            <Save size={18} />
                            {savingProfile ? 'Đang lưu' : 'Lưu thông tin'}
                        </button>
                    </form>

                    <section className={cx('panel')}>
                        <div className={cx('sectionTitle')}>
                            <MapPin size={20} />
                            <h2>Địa chỉ</h2>
                        </div>

                        {showAddressForm ? (
                            <form className={cx('addressForm')} onSubmit={saveAddress}>
                                <div className={cx('formGrid')}>
                                    <label>
                                        Loại địa chỉ
                                        <select
                                            value={addressForm.address_type}
                                            onChange={(e) => updateAddressField('address_type', e.target.value)}
                                        >
                                            <option value="SHIPPING">Giao hàng</option>
                                            <option value="BILLING">Thanh toán</option>
                                        </select>
                                    </label>
                                    <label>
                                        Tên người nhận
                                        <input
                                            value={addressForm.recipient_name}
                                            onChange={(e) => updateAddressField('recipient_name', e.target.value)}
                                            required
                                        />
                                    </label>
                                    <label>
                                        Số điện thoại người nhận
                                        <input
                                            value={addressForm.phone_number}
                                            onChange={(e) => updateAddressField('phone_number', e.target.value)}
                                            required
                                        />
                                    </label>
                                    <label>
                                        Tỉnh/Thành
                                        <input
                                            value={addressForm.province || ''}
                                            onChange={(e) => updateAddressField('province', e.target.value)}
                                        />
                                    </label>
                                    <label>
                                        Quận/Huyện
                                        <input
                                            value={addressForm.district || ''}
                                            onChange={(e) => updateAddressField('district', e.target.value)}
                                        />
                                    </label>
                                    <label>
                                        Phường/Xã
                                        <input
                                            value={addressForm.ward || ''}
                                            onChange={(e) => updateAddressField('ward', e.target.value)}
                                        />
                                    </label>
                                    <label className={cx('wide')}>
                                        Địa chỉ
                                        <input
                                            value={addressForm.address_line1}
                                            onChange={(e) => updateAddressField('address_line1', e.target.value)}
                                            required
                                        />
                                    </label>
                                    <label className={cx('wide')}>
                                        Ghi chú địa chỉ
                                        <input
                                            value={addressForm.address_line2 || ''}
                                            onChange={(e) => updateAddressField('address_line2', e.target.value)}
                                        />
                                    </label>
                                    <label className={cx('toggleRow')}>
                                        <input
                                            type="checkbox"
                                            checked={Boolean(addressForm.is_default)}
                                            onChange={(e) => updateAddressField('is_default', e.target.checked)}
                                        />
                                        Đặt làm mặc định
                                    </label>
                                </div>

                                <div className={cx('buttonRow')}>
                                    <button type="submit" className={cx('primaryButton')} disabled={savingAddress}>
                                        {editingAddressId ? <Save size={18} /> : <Plus size={18} />}
                                        {editingAddressId ? 'Lưu địa chỉ' : 'Thêm địa chỉ'}
                                    </button>
                                    <button type="button" className={cx('ghostButton')} onClick={resetAddressForm}>
                                        Hủy
                                    </button>
                                </div>
                            </form>
                        ) : (
                            <div style={{ marginBottom: '24px' }}>
                                <button
                                    type="button"
                                    className={cx('primaryButton')}
                                    onClick={() => {
                                        resetAddressForm();
                                        setShowAddressForm(true);
                                    }}
                                >
                                    <Plus size={18} />
                                    Thêm địa chỉ
                                </button>
                            </div>
                        )}

                        <div className={cx('addressList')}>
                            {showAddressForm ? (
                                addresses.map((address) => (
                                    <article className={cx('addressItem')} key={address.id}>
                                        <div>
                                            <div className={cx('addressHeader')}>
                                                <strong>{address.recipient_name}</strong>
                                                {address.is_default && (
                                                    <span>
                                                        <CheckCircle size={14} />
                                                        Mặc định
                                                    </span>
                                                )}
                                            </div>
                                            <p>{address.phone_number}</p>
                                            <p>
                                                {[address.address_line1, address.ward, address.district, address.province]
                                                    .filter(Boolean)
                                                    .join(', ')}
                                            </p>
                                        </div>
                                        <div className={cx('iconActions')}>
                                            <button type="button" onClick={() => editAddress(address)} aria-label="Sửa địa chỉ">
                                                <Pencil size={16} />
                                            </button>
                                            <button type="button" onClick={() => deleteAddress(address.id)} aria-label="Xóa địa chỉ">
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </article>
                                ))
                            ) : (
                                addresses
                                    .filter((address) => address.is_default)
                                    .map((address) => (
                                        <article className={cx('addressItem')} key={address.id}>
                                            <div>
                                                <div className={cx('addressHeader')}>
                                                    <strong>{address.recipient_name}</strong>
                                                    <span>
                                                        <CheckCircle size={14} />
                                                        Mặc định
                                                    </span>
                                                </div>
                                                <p>{address.phone_number}</p>
                                                <p>
                                                    {[address.address_line1, address.ward, address.district, address.province]
                                                        .filter(Boolean)
                                                        .join(', ')}
                                                </p>
                                            </div>
                                            <div className={cx('iconActions')}>
                                                <button type="button" onClick={() => editAddress(address)} aria-label="Sửa địa chỉ">
                                                    <Pencil size={16} />
                                                </button>
                                                <button type="button" onClick={() => deleteAddress(address.id)} aria-label="Xóa địa chỉ">
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        </article>
                                    ))
                            )}
                            {!addresses.length && <p className={cx('emptyText')}>Chưa có địa chỉ.</p>}
                            {!showAddressForm && addresses.length > 0 && !addresses.some(a => a.is_default) && (
                                <p className={cx('emptyText')}>Chưa cấu hình địa chỉ mặc định. Bấm "Thêm địa chỉ" hoặc chỉnh sửa địa chỉ sẵn có làm mặc định.</p>
                            )}
                        </div>
                    </section>
                </section>
            </main>
            <Footer />
            <ChangePassword
                show={showChangePass}
                setShow={setShowChangePass}
                email={profile.email}
                passwordLoginEnabled={profile.password_login_enabled}
                onPasswordChanged={async () => {
                    const nextProfile = await fetchProfile();
                    setProfile(nextProfile);
                    setProfileForm(nextProfile);
                }}
            />
        </div>
    );
}

export default InfoUser;
