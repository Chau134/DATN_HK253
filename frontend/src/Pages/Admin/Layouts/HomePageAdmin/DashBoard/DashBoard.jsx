import classNames from 'classnames/bind';
import styles from './DashBoard.module.scss';
import { useEffect, useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChartSimple, faUser } from '@fortawesome/free-solid-svg-icons';

import request from '../../../../../config/Connect';
import { fetchAdminOrders } from '../../../../../api/adminCatalogApi';
import { fetchAdminCustomers } from '../../../../../api/adminCustomerApi';

import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const cx = classNames.bind(styles);

const dateKey = (value) => {
    if (!value) return 'N/A';
    return new Date(value).toLocaleDateString('vi-VN');
};

function Dashboard() {
    const [dataUser, setDataUser] = useState({});
    const [chartData, setChartData] = useState({
        labels: [],
        datasets: [
            {
                label: 'Doanh thu (VNĐ)',
                data: [],
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.4,
            },
        ],
    });
    const [lengthUser, setLengthUser] = useState(0);
    const [sumPirce, setSumPirce] = useState(0);

    useEffect(() => {
        request.get('/api/me').then((res) => setDataUser(res.data));

        fetchAdminCustomers()
            .then((customers) => {
                setLengthUser(customers.length);
            })
            .catch(() => setLengthUser(0));

        fetchAdminOrders()
            .then((orders) => {
                const completedOrders = orders.filter((order) => order.status === 'COMPLETED');
                const revenueByDate = completedOrders.reduce((acc, order) => {
                    const key = dateKey(order.updated_at || order.placed_at || order.created_at);
                    acc[key] = (acc[key] || 0) + Number(order.total_amount || 0);
                    return acc;
                }, {});

                const labels = Object.keys(revenueByDate);
                const data = labels.map((label) => revenueByDate[label]);
                setSumPirce(data.reduce((total, item) => total + item, 0));
                setChartData((prev) => ({
                    ...prev,
                    labels,
                    datasets: [
                        {
                            ...prev.datasets[0],
                            data,
                        },
                    ],
                }));
            })
            .catch(() => null);
    }, []);

    const options = {
        responsive: true,
        plugins: {
            legend: {
                position: 'top',
            },
            title: {
                display: true,
                text: 'Thống kê doanh thu đơn khách đã xác nhận nhận hàng',
            },
        },
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('thong-ke')}>
                <div className={cx('chart-line')}>
                    <div className={cx('box-1')}>
                        <h4>Tổng doanh thu đã hoàn thành</h4>
                        <FontAwesomeIcon icon={faChartSimple} />
                        <span>{sumPirce.toLocaleString()} VNĐ</span>
                    </div>
                    <div className={cx('box-3')}>
                        <h4>Tổng người dùng</h4>
                        <FontAwesomeIcon icon={faUser} />
                        <span>{lengthUser} Người dùng</span>
                    </div>
                </div>
                <div className={cx('info-user')}>
                    <img src={dataUser?.avatar_url || 'https://ui-avatars.com/api/?name=Admin'} alt="Avatar" />
                    <div className={cx('info')}>
                        <h2>
                            {dataUser?.full_name ||
                                dataUser?.fullName ||
                                dataUser?.display_name ||
                                dataUser?.displayName ||
                                dataUser?.email}
                        </h2>
                        <span>{dataUser?.phone_number || dataUser?.phoneNumber || ''}</span>
                        <span>{dataUser?.email}</span>
                        <span>Chức vụ: {dataUser?.roles?.includes('ADMIN') ? 'Admin' : 'Customer'}</span>
                    </div>
                </div>
            </div>

            <div className={cx('chart-line-2')}>
                <Line data={chartData} options={options} />
            </div>
        </div>
    );
}

export default Dashboard;
