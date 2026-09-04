import React from 'react';
import classNames from 'classnames/bind';
import { Check, Clock, Package, Truck, Home, X } from 'lucide-react';
import styles from './OrderTimeline.module.scss';

const cx = classNames.bind(styles);

const STAGES = [
    { key: 'PENDING', label: 'Đã đặt hàng', icon: Clock },
    { key: 'CONFIRMED', label: 'Đã xác nhận', icon: Check },
    { key: 'PACKING', label: 'Đang đóng gói', icon: Package },
    { key: 'SHIPPING', label: 'Đang vận chuyển', icon: Truck },
    { key: 'COMPLETED', label: 'Đã giao hàng', icon: Home },
];

// Map every backend status onto a stage index in STAGES
const STATUS_TO_INDEX = {
    PENDING: 0,
    CONFIRMED: 1,
    PAID: 1,
    PACKING: 2,
    SHIPPING: 3,
    DELIVERED: 4,
    COMPLETED: 4,
};

function OrderTimeline({ status }) {
    const isCancelled = ['CANCELLED', 'REFUNDED'].includes(status);

    if (isCancelled) {
        return (
            <div className={cx('cancelled')}>
                <span className={cx('cancelled-icon')}>
                    <X size={18} />
                </span>
                <span>{status === 'REFUNDED' ? 'Đơn hàng đã được hoàn tiền' : 'Đơn hàng đã bị hủy'}</span>
            </div>
        );
    }

    const currentIndex = STATUS_TO_INDEX[status] ?? 0;

    return (
        <div className={cx('timeline')} role="list" aria-label="Trạng thái đơn hàng">
            {STAGES.map((stage, index) => {
                const Icon = stage.icon;
                const isDone = index < currentIndex;
                const isCurrent = index === currentIndex;
                const state = isDone ? 'done' : isCurrent ? 'current' : 'upcoming';

                return (
                    <div key={stage.key} className={cx('stage', state)} role="listitem">
                        {index > 0 && <span className={cx('connector', index <= currentIndex && 'connector-active')} />}
                        <span className={cx('dot')}>
                            {isDone ? <Check size={16} /> : <Icon size={16} />}
                        </span>
                        <span className={cx('label')}>{stage.label}</span>
                    </div>
                );
            })}
        </div>
    );
}

export default OrderTimeline;
