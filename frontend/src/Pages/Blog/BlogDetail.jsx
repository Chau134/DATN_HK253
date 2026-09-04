import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import classNames from 'classnames/bind';
import styles from './BlogDetail.module.scss';
import Header from '../../Layouts/Header/Header';
import Footer from '../../Layouts/Footer/Footer';
import request, { getApiError } from '../../config/Connect';
import { toast, ToastContainer } from 'react-toastify';

const cx = classNames.bind(styles);

const CATEGORY_MAP = {
    FASHION: 'Thời trang',
    SHOES: 'Giày dép',
    PROMOTION: 'Khuyến mãi',
    SHOPPING_GUIDE: 'Hướng dẫn mua sắm',
    AI_TIPS: 'Mẹo AI tư vấn'
};

function BlogDetail() {
    const { id } = useParams(); // 'id' contains the slug from path '/blog/:id'
    const [blog, setBlog] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        request.get(`/api/blogs/slug/${id}`)
            .then((res) => {
                setBlog(res.data);
                setLoading(false);
            })
            .catch((err) => {
                console.error(err);
                toast.error(getApiError(err, 'Không thể tải chi tiết bài viết'));
                setLoading(false);
            });
    }, [id]);

    const formatDate = (dateStr) => {
        if (!dateStr) return 'Bản nháp';
        const date = new Date(dateStr);
        return date.toLocaleDateString('vi-VN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const isHtml = (str) => {
        if (!str) return false;
        return /<[a-z][\s\S]*>/i.test(str);
    };

    return (
        <div className={cx('wrapper')}>
            <Header />
            
            <main className={cx('container')}>
                <div className={cx('back-btn-container')}>
                    <Link to="/blog" className={cx('back-btn')}>
                        &larr; Quay lại danh sách
                    </Link>
                </div>

                {loading ? (
                    <div className={cx('loading-spinner')}>
                        <div className={cx('spinner')}></div>
                        <p>Đang tải bài viết...</p>
                    </div>
                ) : blog ? (
                    <article className={cx('article-card')}>
                        <header className={cx('article-header')}>
                            <span className="badge bg-danger mb-2 p-2 fs-6">
                                {CATEGORY_MAP[blog.category] || blog.category}
                            </span>
                            <h1 className={cx('article-title')}>{blog.title}</h1>
                            <div className={cx('article-meta')}>
                                <span className={cx('meta-author')}>
                                    Tác giả: <strong>{blog.author_name || 'Ẩn danh'}</strong>
                                </span>
                                <span className="mx-2">|</span>
                                <span className={cx('meta-date')}>
                                    Xuất bản: {formatDate(blog.published_at || blog.publishedAt)}
                                </span>
                            </div>
                        </header>

                        {blog.thumbnail_url && (
                            <div className={cx('image-wrapper')}>
                                <img src={blog.thumbnail_url} alt={blog.title} className={cx('article-image')} />
                            </div>
                        )}

                        {blog.summary && (
                            <div className={cx('article-description')}>
                                <p>{blog.summary}</p>
                            </div>
                        )}

                        <div className={cx('article-content')}>
                            {isHtml(blog.content) ? (
                                <div dangerouslySetInnerHTML={{ __html: blog.content }} />
                            ) : (
                                blog.content?.split('\n').map((para, idx) => (
                                    <p key={idx}>{para}</p>
                                ))
                            )}
                        </div>
                    </article>
                ) : (
                    <div className={cx('error-state')}>
                        <h3>Không tìm thấy bài viết</h3>
                        <p>Bài viết này không tồn tại hoặc đã bị gỡ bỏ.</p>
                        <Link to="/blog" className={cx('back-home-btn')}>Trở về trang chủ Blog</Link>
                    </div>
                )}
            </main>

            <Footer />
            <ToastContainer />
        </div>
    );
}

export default BlogDetail;
