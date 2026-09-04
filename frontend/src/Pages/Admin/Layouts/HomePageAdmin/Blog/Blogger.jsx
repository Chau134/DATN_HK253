import React, { useEffect, useState } from 'react';
import { toast, ToastContainer } from 'react-toastify';
import request from '../../../../../config/Connect';
import { EditBlog, ModalAddBlog } from '../../../Modal/Modal';

import classNames from 'classnames/bind';
import styles from './Blog.module.scss';
const cx = classNames.bind(styles);

const STATUS_MAP = {
    DRAFT: { label: 'Bản nháp', badge: 'bg-secondary' },
    PUBLISHED: { label: 'Đã xuất bản', badge: 'bg-success' },
    ARCHIVED: { label: 'Lưu trữ', badge: 'bg-warning text-dark' }
};

const CATEGORY_MAP = {
    FASHION: 'Thời trang',
    SHOES: 'Giày dép',
    PROMOTION: 'Khuyến mãi',
    SHOPPING_GUIDE: 'Hướng dẫn mua sắm',
    AI_TIPS: 'Mẹo AI tư vấn'
};

function BlogAdmin() {
    const [showAdd, setShowAdd] = useState(false);
    const [showEdit, setShowEdit] = useState(false);
    const [dataBlog, setDataBlog] = useState([]);
    const [selectedId, setSelectedId] = useState(null);

    // Load blog
    const fetchBlogs = async () => {
        try {
            const res = await request.get('/admin/blogs');
            setDataBlog(res.data || []);
        } catch (error) {
            console.error('Lỗi khi tải bài viết:', error);
            toast.error('Không thể tải danh sách bài viết');
        }
    };

    useEffect(() => {
        fetchBlogs();
    }, [showAdd, showEdit]);

    // Delete blog
    const handleDeleteBlog = async (id) => {
        if (!window.confirm('Bạn có chắc chắn muốn xóa bài viết này?')) return;
        if (!window.confirm(`Xác nhận lần 2: xóa chính thức bài viết có ID ${id}?`)) return;

        try {
            await request.delete(`/admin/blogs/${id}`);
            toast.success('Xóa bài viết thành công!');
            fetchBlogs();
        } catch (error) {
            console.error(error);
            toast.error('Xóa bài viết thất bại!');
        }
    };

    return (
        <div className={cx('wrapper')}>
            <div className={cx('btn-addBlog')}>
                <h1>Quản lý bài viết</h1>
                <button
                    className="btn btn-primary"
                    onClick={() => setShowAdd(true)}
                >
                    Thêm bài viết
                </button>
            </div>

            <table className="table table-striped table-bordered mt-3 text-white">
                <thead>
                    <tr>
                        <th className="text-white">#</th>
                        <th className="text-white">Ảnh</th>
                        <th className="text-white">Tiêu đề</th>
                        <th className="text-white">Danh mục</th>
                        <th className="text-white">Trạng thái</th>
                        <th className="text-white">Tác giả</th>
                        <th className="text-white">Hành động</th>
                    </tr>
                </thead>

                <tbody>
                    {dataBlog.length === 0 && (
                        <tr>
                            <td colSpan="7" style={{ textAlign: 'center', color: '#fff' }}>
                                Chưa có bài viết nào
                            </td>
                        </tr>
                    )}

                    {dataBlog.map((item, index) => (
                        <tr key={item.id}>
                            <td style={{ color: '#fff' }}>{index + 1}</td>

                            <td>
                                {item.thumbnail_url ? (
                                    <img
                                        src={item.thumbnail_url}
                                        alt={item.title}
                                        style={{ width: '100px', borderRadius: '6px', height: '60px', objectFit: 'cover' }}
                                    />
                                ) : (
                                    <span style={{ fontSize: '0.85rem', color: '#ccc' }}>Không có ảnh</span>
                                )}
                            </td>

                            <td style={{ color: '#fff', fontWeight: 'bold' }}>{item.title}</td>
                            <td style={{ color: '#fff' }}>{CATEGORY_MAP[item.category] || item.category}</td>
                            <td style={{ color: '#fff' }}>
                                <span className={`badge ${STATUS_MAP[item.status]?.badge || 'bg-light'}`}>
                                    {STATUS_MAP[item.status]?.label || item.status}
                                </span>
                            </td>
                            <td style={{ color: '#fff' }}>{item.author_name || 'Ẩn danh'}</td>

                            <td>
                                <button
                                    className="btn btn-warning me-2 text-dark font-weight-bold"
                                    onClick={() => {
                                        setSelectedId(item.id);
                                        setShowEdit(true);
                                    }}
                                >
                                    Sửa
                                </button>

                                <button
                                    className="btn btn-danger"
                                    onClick={() => handleDeleteBlog(item.id)}
                                >
                                    Xóa
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <ToastContainer />

            <ModalAddBlog show={showAdd} setShow={setShowAdd} />
            <EditBlog show={showEdit} setShow={setShowEdit} id={selectedId} />
        </div>
    );
}

export default BlogAdmin;
