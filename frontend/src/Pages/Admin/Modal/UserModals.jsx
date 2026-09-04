import React, { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import { toast, ToastContainer } from 'react-toastify';

export function ModalEditUser({ show, setShow, email }) {
    const [valueSelect, setValueSelect] = useState('0');

    const handleEditUser = async () => {
        toast.error('Spring Boot hiện chưa có endpoint cập nhật quyền người dùng.');
    };

    const handleClose = () => setShow(false);

    return (
        <Modal show={show} onHide={handleClose}>
            <ToastContainer />
            <Modal.Header closeButton>
                <Modal.Title>Chỉnh Sửa Quyền </Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <select
                    onChange={(e) => setValueSelect(e.target.value)}
                    className="form-select"
                    aria-label="Default select example"
                >
                    <option selected>Chọn quyền</option>
                    <option value="1">Người Dùng</option>
                    <option value="3">Người Quản Trị</option>
                </select>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleClose}>
                    Đóng
                </Button>
                <Button variant="primary" onClick={handleEditUser}>
                    Lưu Lại
                </Button>
            </Modal.Footer>
        </Modal>
    );
}

