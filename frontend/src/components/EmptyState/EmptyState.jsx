import React from 'react';
import classNames from 'classnames/bind';
import styles from './EmptyState.module.scss';
import { Link } from 'react-router-dom';

const cx = classNames.bind(styles);

const EmptyState = ({
    type = 'cart',
    title,
    description,
    actionText,
    actionLink,
    onAction
}) => {
    const getDefaultContent = () => {
        switch (type) {
            case 'cart':
                return {
                    title: 'Giỏ hàng trống',
                    description: 'Bạn chưa có sản phẩm nào trong giỏ hàng. Hãy khám phá và thêm sản phẩm yêu thích!',
                    actionText: 'Khám phá sản phẩm',
                    actionLink: '/product',
                    icon: (
                        <svg viewBox="0 0 200 200" className={cx('empty-icon')}>
                            <circle cx="100" cy="100" r="80" fill="#f8f9fa" stroke="#dee2e6" strokeWidth="2"/>
                            <path d="M60 80 L140 80 L135 120 L65 120 Z" fill="#e9ecef" stroke="#adb5bd" strokeWidth="2"/>
                            <circle cx="75" cy="140" r="8" fill="#6c757d"/>
                            <circle cx="125" cy="140" r="8" fill="#6c757d"/>
                            <path d="M80 90 L120 90" stroke="#adb5bd" strokeWidth="3" strokeLinecap="round"/>
                        </svg>
                    )
                };
            case 'wishlist':
                return {
                    title: 'Chưa có sản phẩm yêu thích',
                    description: 'Bạn chưa lưu sản phẩm nào vào danh sách yêu thích. Hãy khám phá và lưu những sản phẩm bạn thích!',
                    actionText: 'Khám phá ngay',
                    actionLink: '/product',
                    icon: (
                        <svg viewBox="0 0 200 200" className={cx('empty-icon')}>
                            <circle cx="100" cy="100" r="80" fill="#fff0f6" stroke="#ffcce5" strokeWidth="2"/>
                            <path d="M100 140 L65 105 Q65 75 85 75 Q100 75 100 90 Q100 75 115 75 Q135 75 135 105 Z"
                                  fill="#ffe4f0" stroke="#ff99cc" strokeWidth="2"/>
                        </svg>
                    )
                };
            case 'orders':
                return {
                    title: 'Chưa có đơn hàng nào',
                    description: 'Bạn chưa đặt đơn hàng nào. Hãy khám phá các sản phẩm và bắt đầu mua sắm!',
                    actionText: 'Mua sắm ngay',
                    actionLink: '/product',
                    icon: (
                        <svg viewBox="0 0 200 200" className={cx('empty-icon')}>
                            <circle cx="100" cy="100" r="80" fill="#f0f8ff" stroke="#cce5ff" strokeWidth="2"/>
                            <rect x="70" y="70" width="60" height="50" fill="#e6f2ff" stroke="#99ccff" strokeWidth="2" rx="4"/>
                            <path d="M85 85 L115 85 M85 95 L110 95 M85 105 L105 105"
                                  stroke="#66b3ff" strokeWidth="2" strokeLinecap="round"/>
                        </svg>
                    )
                };
            case 'notifications':
                return {
                    title: 'Không có thông báo mới',
                    description: 'Bạn đã xem hết tất cả thông báo.',
                    actionText: null,
                    actionLink: null,
                    icon: (
                        <svg viewBox="0 0 200 200" className={cx('empty-icon')}>
                            <circle cx="100" cy="100" r="80" fill="#fffbf0" stroke="#ffe6b3" strokeWidth="2"/>
                            <path d="M100 70 Q85 70 85 85 L85 105 Q85 115 75 120 L125 120 Q115 115 115 105 L115 85 Q115 70 100 70 Z"
                                  fill="#fff5cc" stroke="#ffcc66" strokeWidth="2"/>
                            <circle cx="100" cy="130" r="5" fill="#ffcc66"/>
                        </svg>
                    )
                };
            case 'search':
                return {
                    title: 'Không tìm thấy kết quả',
                    description: 'Không tìm thấy sản phẩm nào phù hợp với tìm kiếm của bạn. Hãy thử lại với từ khóa khác!',
                    actionText: 'Xóa bộ lọc',
                    actionLink: null,
                    icon: (
                        <svg viewBox="0 0 200 200" className={cx('empty-icon')}>
                            <circle cx="100" cy="100" r="80" fill="#f5f5f5" stroke="#d9d9d9" strokeWidth="2"/>
                            <circle cx="90" cy="90" r="25" fill="none" stroke="#999" strokeWidth="3"/>
                            <path d="M108 108 L130 130" stroke="#999" strokeWidth="3" strokeLinecap="round"/>
                            <path d="M80 85 L100 85 M90 75 L90 95" stroke="#ccc" strokeWidth="2" strokeLinecap="round"/>
                        </svg>
                    )
                };
            default:
                return {
                    title: 'Không có dữ liệu',
                    description: 'Hiện tại không có dữ liệu để hiển thị.',
                    actionText: null,
                    actionLink: null,
                    icon: (
                        <svg viewBox="0 0 200 200" className={cx('empty-icon')}>
                            <circle cx="100" cy="100" r="80" fill="#f8f9fa" stroke="#dee2e6" strokeWidth="2"/>
                        </svg>
                    )
                };
        }
    };

    const defaultContent = getDefaultContent();
    const finalTitle = title || defaultContent.title;
    const finalDescription = description || defaultContent.description;
    const finalActionText = actionText !== undefined ? actionText : defaultContent.actionText;
    const finalActionLink = actionLink !== undefined ? actionLink : defaultContent.actionLink;

    return (
        <div className={cx('empty-state')}>
            <div className={cx('empty-icon-wrapper')}>
                {defaultContent.icon}
            </div>
            <h3 className={cx('empty-title')}>{finalTitle}</h3>
            <p className={cx('empty-description')}>{finalDescription}</p>
            {finalActionText && (
                finalActionLink ? (
                    <Link to={finalActionLink} className={cx('empty-action')}>
                        {finalActionText}
                    </Link>
                ) : (
                    <button
                        type="button"
                        onClick={onAction}
                        className={cx('empty-action')}
                    >
                        {finalActionText}
                    </button>
                )
            )}
        </div>
    );
};

export default EmptyState;
