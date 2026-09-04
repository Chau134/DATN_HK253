import React, { useState, useEffect } from 'react';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import { toast } from 'react-toastify';
import request, { getApiError } from '../../../config/Connect';

const getLocalDatetimeString = (date) => {
    if (!date) return '';
    const tzoffset = date.getTimezoneOffset() * 60000;
    return new Date(date - tzoffset).toISOString().slice(0, 16);
};

export function ModalAddBlog({ show, setShow }) {
    const handleClose = () => {
        setShow(false);
        // Clear fields
        setImg(null);
        setTitle('');
        setDes('');
        setContent('');
        setCategory('FASHION');
        setStatus('DRAFT');
        setPublishedAt(getLocalDatetimeString(new Date()));
    };

    const [img, setImg] = useState(null);
    const [title, setTitle] = useState('');
    const [des, setDes] = useState('');
    const [content, setContent] = useState('');
    const [category, setCategory] = useState('FASHION');
    const [status, setStatus] = useState('DRAFT');
    const [publishedAt, setPublishedAt] = useState('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (show) {
            setPublishedAt(getLocalDatetimeString(new Date()));
        }
    }, [show]);

    const handleAddBlog = async () => {
        if (!title.trim()) {
            toast.error('Vui lòng nhập tên bài viết!');
            return;
        }
        if (!content.trim()) {
            toast.error('Vui lòng nhập nội dung chi tiết!');
            return;
        }

        setSubmitting(true);
        try {
            const formData = new FormData();
            formData.append('title', title);
            formData.append('summary', des);
            formData.append('content', content);
            formData.append('category', category);
            formData.append('status', status);
            if (publishedAt) {
                formData.append('published_at', new Date(publishedAt).toISOString());
            }
            if (img) {
                formData.append('file', img);
            }

            await request.post('/admin/blogs', formData);
            toast.success('Thêm bài viết thành công!');
            handleClose();
        } catch (error) {
            console.error(error);
            toast.error(getApiError(error, 'Thêm bài viết thất bại!'));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Thêm Bài Viết</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <h5 className="border-bottom pb-2 mb-3 text-primary">Thông tin cơ bản</h5>
                
                <div className="mb-3">
                    <label className="form-label font-weight-bold">Tiêu Đề Bài Viết *</label>
                    <input
                        type="text"
                        className="form-control"
                        placeholder="Nhập tiêu đề bài viết..."
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                    />
                </div>

                <div className="mb-3">
                    <label className="form-label font-weight-bold">Mô Tả Ngắn</label>
                    <textarea
                        className="form-control"
                        rows="2"
                        placeholder="Nhập mô tả ngắn cho bài viết..."
                        value={des}
                        onChange={(e) => setDes(e.target.value)}
                    />
                </div>

                <div className="row">
                    <div className="col-md-6 mb-3">
                        <label className="form-label font-weight-bold">Danh Mục *</label>
                        <select
                            className="form-select"
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                        >
                            <option value="FASHION">Thời trang</option>
                            <option value="SHOES">Giày dép</option>
                            <option value="PROMOTION">Khuyến mãi</option>
                            <option value="SHOPPING_GUIDE">Hướng dẫn mua sắm</option>
                            <option value="AI_TIPS">Mẹo AI tư vấn</option>
                        </select>
                    </div>

                    <div className="col-md-6 mb-3">
                        <label className="form-label font-weight-bold">Ảnh Đại Diện (Thumbnail)</label>
                        <input
                            className="form-control"
                            type="file"
                            accept="image/*"
                            onChange={(e) => setImg(e.target.files[0])}
                        />
                    </div>
                </div>

                <h5 className="border-bottom pb-2 mt-4 mb-3 text-primary">Nội dung</h5>

                <div className="mb-3">
                    <label className="form-label font-weight-bold">Nội Dung Chi Tiết (HTML/Rich Text) *</label>
                    <textarea
                        className="form-control"
                        rows="8"
                        placeholder="Nhập nội dung chi tiết bài viết (chấp nhận thẻ HTML)..."
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                    />
                </div>

                <h5 className="border-bottom pb-2 mt-4 mb-3 text-primary">Xuất bản</h5>

                <div className="row">
                    <div className="col-md-6 mb-3">
                        <label className="form-label font-weight-bold">Trạng Thái *</label>
                        <select
                            className="form-select"
                            value={status}
                            onChange={(e) => setStatus(e.target.value)}
                        >
                            <option value="DRAFT">Bản nháp (Draft)</option>
                            <option value="PUBLISHED">Công khai (Published)</option>
                            <option value="ARCHIVED">Lưu trữ (Archived)</option>
                        </select>
                    </div>

                    <div className="col-md-6 mb-3">
                        <label className="form-label font-weight-bold">Ngày Đăng (Trống = Hiện tại)</label>
                        <input
                            type="datetime-local"
                            className="form-control"
                            value={publishedAt}
                            onChange={(e) => setPublishedAt(e.target.value)}
                        />
                    </div>
                </div>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose} disabled={submitting}>
                    Đóng
                </Button>
                <Button variant="primary" onClick={handleAddBlog} disabled={submitting}>
                    {submitting ? 'Đang lưu...' : 'Thêm Bài Viết'}
                </Button>
            </Modal.Footer>
        </Modal>
    );
}

export function EditBlog({ show, setShow, id }) {
    const handleClose = () => {
        setShow(false);
        setImgBlog(null);
    };

    const [imgBlog, setImgBlog] = useState(null);
    const [titleBlog, setTitleBlog] = useState('');
    const [desBlog, setDesBlog] = useState('');
    const [contentBlog, setContentBlog] = useState('');
    const [categoryBlog, setCategoryBlog] = useState('FASHION');
    const [statusBlog, setStatusBlog] = useState('DRAFT');
    const [publishedAtBlog, setPublishedAtBlog] = useState('');
    const [existingImg, setExistingImg] = useState('');
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (show && id) {
            setLoading(true);
            request.get(`/admin/blogs/${id}`)
                .then((res) => {
                    const blog = res.data;
                    setTitleBlog(blog.title || '');
                    setDesBlog(blog.summary || '');
                    setContentBlog(blog.content || '');
                    setCategoryBlog(blog.category || 'FASHION');
                    setStatusBlog(blog.status || 'DRAFT');
                    setExistingImg(blog.thumbnail_url || '');
                    
                    if (blog.published_at) {
                        const date = new Date(blog.published_at);
                        setPublishedAtBlog(getLocalDatetimeString(date));
                    } else {
                        setPublishedAtBlog('');
                    }
                    setLoading(false);
                })
                .catch((err) => {
                    console.error(err);
                    toast.error('Không thể lấy thông tin chi tiết bài viết');
                    setLoading(false);
                });
        }
    }, [show, id]);

    const handleEditBlog = async () => {
        if (!titleBlog.trim()) {
            toast.error('Vui lòng nhập tên bài viết!');
            return;
        }
        if (!contentBlog.trim()) {
            toast.error('Vui lòng nhập nội dung chi tiết!');
            return;
        }

        setSubmitting(true);
        try {
            const formData = new FormData();
            formData.append('title', titleBlog);
            formData.append('summary', desBlog);
            formData.append('content', contentBlog);
            formData.append('category', categoryBlog);
            formData.append('status', statusBlog);
            formData.append('img', existingImg || '');
            
            if (publishedAtBlog) {
                formData.append('published_at', new Date(publishedAtBlog).toISOString());
            } else {
                formData.append('published_at', '');
            }

            if (imgBlog) {
                formData.append('file', imgBlog);
            }

            await request.put(`/admin/blogs/${id}`, formData);
            toast.success('Chỉnh sửa bài viết thành công!');
            handleClose();
        } catch (error) {
            console.error(error);
            toast.error(getApiError(error, 'Chỉnh sửa bài viết thất bại!'));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Modal show={show} onHide={handleClose} size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Chỉnh Sửa Bài Viết</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                {loading ? (
                    <div className="text-center my-3">Đang tải thông tin bài viết...</div>
                ) : (
                    <>
                        <h5 className="border-bottom pb-2 mb-3 text-primary">Thông tin cơ bản</h5>

                        <div className="mb-3">
                            <label className="form-label font-weight-bold">Tiêu Đề Bài Viết *</label>
                            <input
                                type="text"
                                className="form-control"
                                value={titleBlog}
                                onChange={(e) => setTitleBlog(e.target.value)}
                            />
                        </div>

                        <div className="mb-3">
                            <label className="form-label font-weight-bold">Mô Tả Ngắn</label>
                            <textarea
                                className="form-control"
                                rows="2"
                                value={desBlog}
                                onChange={(e) => setDesBlog(e.target.value)}
                            />
                        </div>

                        <div className="row">
                            <div className="col-md-6 mb-3">
                                <label className="form-label font-weight-bold">Danh Mục *</label>
                                <select
                                    className="form-select"
                                    value={categoryBlog}
                                    onChange={(e) => setCategoryBlog(e.target.value)}
                                >
                                    <option value="FASHION">Thời trang</option>
                                    <option value="SHOES">Giày dép</option>
                                    <option value="PROMOTION">Khuyến mãi</option>
                                    <option value="SHOPPING_GUIDE">Hướng dẫn mua sắm</option>
                                    <option value="AI_TIPS">Mẹo AI tư vấn</option>
                                </select>
                            </div>

                            <div className="col-md-6 mb-3">
                                <label className="form-label font-weight-bold">Thay Đổi Ảnh Bài Viết (Tùy chọn)</label>
                                <input
                                    className="form-control"
                                    type="file"
                                    accept="image/*"
                                    onChange={(e) => setImgBlog(e.target.files[0])}
                                />
                            </div>
                        </div>

                        {existingImg && (
                            <div className="mb-3">
                                <label className="form-label font-weight-bold d-block">Ảnh Đại Diện Hiện Tại</label>
                                <img
                                    src={existingImg}
                                    alt="Current blog"
                                    style={{ width: '150px', borderRadius: '8px', objectFit: 'cover', height: '100px' }}
                                />
                            </div>
                        )}

                        <h5 className="border-bottom pb-2 mt-4 mb-3 text-primary">Nội dung</h5>

                        <div className="mb-3">
                            <label className="form-label font-weight-bold">Nội Dung Chi Tiết (HTML/Rich Text) *</label>
                            <textarea
                                className="form-control"
                                rows="8"
                                value={contentBlog}
                                onChange={(e) => setContentBlog(e.target.value)}
                            />
                        </div>

                        <h5 className="border-bottom pb-2 mt-4 mb-3 text-primary">Xuất bản</h5>

                        <div className="row">
                            <div className="col-md-6 mb-3">
                                <label className="form-label font-weight-bold">Trạng Thế *</label>
                                <select
                                    className="form-select"
                                    value={statusBlog}
                                    onChange={(e) => setStatusBlog(e.target.value)}
                                >
                                    <option value="DRAFT">Bản nháp (Draft)</option>
                                    <option value="PUBLISHED">Công khai (Published)</option>
                                    <option value="ARCHIVED">Lưu trữ (Archived)</option>
                                </select>
                            </div>

                            <div className="col-md-6 mb-3">
                                <label className="form-label font-weight-bold">Ngày Đăng</label>
                                <input
                                    type="datetime-local"
                                    className="form-control"
                                    value={publishedAtBlog}
                                    onChange={(e) => setPublishedAtBlog(e.target.value)}
                                />
                            </div>
                        </div>
                    </>
                )}
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose} disabled={submitting}>
                    Đóng
                </Button>
                <Button variant="primary" onClick={handleEditBlog} disabled={submitting || loading}>
                    {submitting ? 'Đang lưu...' : 'Lưu Lại'}
                </Button>
            </Modal.Footer>
        </Modal>
    );
}
