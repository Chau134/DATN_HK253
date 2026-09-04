import React, { useEffect, useState } from 'react';
import classNames from 'classnames/bind';

import { deleteAdminCustomer, fetchAdminCustomers } from '../../../../../api/adminCustomerApi';
import { getApiError } from '../../../../../config/Connect';
import styles from './Customers.module.scss';

const cx = classNames.bind(styles);

function Customers() {
    const [customers, setCustomers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [notice, setNotice] = useState(null);

    useEffect(() => {
        loadCustomers();
    }, []);

    const showNotice = (message, type = 'success') => {
        setNotice({ message, type });
        window.clearTimeout(showNotice.timeoutId);
        showNotice.timeoutId = window.setTimeout(() => setNotice(null), 2600);
    };

    const loadCustomers = async () => {
        try {
            setLoading(true);
            const data = await fetchAdminCustomers();
            setCustomers(data);
        } catch (error) {
            showNotice(getApiError(error, 'Không tải được danh sách khách hàng.'), 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteCustomer = async (customerId) => {
        if (!window.confirm('Xóa khách hàng này khỏi danh sách quản lý?')) return;
        if (!window.confirm(`Xác nhận lần 2: xóa chính thức khách hàng có ID ${customerId}?`)) return;

        try {
            await deleteAdminCustomer(customerId);
            showNotice('Đã xóa khách hàng.');
            await loadCustomers();
        } catch (error) {
            showNotice(getApiError(error, 'Không xóa được khách hàng.'), 'error');
        }
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('header')}>
                <h1>Khách hàng</h1>
                <span>{customers.length} customer</span>
            </div>

            {notice && <div className={cx('notice', notice.type === 'error' && 'notice-error')}>{notice.message}</div>}

            <table className={cx('table')}>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Họ tên</th>
                        <th>Email</th>
                        <th>Số điện thoại</th>
                        <th>Vai trò</th>
                        <th>Hành động</th>
                    </tr>
                </thead>
                <tbody>
                    {loading ? (
                        <tr>
                            <td colSpan="6">Đang tải khách hàng...</td>
                        </tr>
                    ) : customers.length === 0 ? (
                        <tr>
                            <td colSpan="6">Chưa có khách hàng.</td>
                        </tr>
                    ) : (
                        customers.map((item) => (
                            <tr key={item.id}>
                                <td>{item.id}</td>
                                <td>{item.full_name || item.display_name || '-'}</td>
                                <td>{item.email}</td>
                                <td>{item.phone_number || '-'}</td>
                                <td>Customer</td>
                                <td>
                                    <button type="button" className={cx('delete-button')} onClick={() => handleDeleteCustomer(item.id)}>
                                        Xóa
                                    </button>
                                </td>
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
        </div>
    );
}

export default Customers;
