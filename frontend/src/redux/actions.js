function addProduct(payload) {
    // tạo hàm addProduct nhận tham số là payload
    return {
        type: 'ADD_PRODUCT', // tạo type la 'ADD_PRODUCT' là action thêm sp mới
        payload, // là dữ liệu bổ sung cho action, chứa thông tin của sp cần đc thêm vào giỏ hàng
    };
}

function removeProduct(payload) {
    console.log(payload);
    return {
        type: 'REMOVE_PRODUCT',
        payload,
    };
}

function clearCart() {
    return {
        type: 'CLEAR_CART',
    };
}

function setCart(payload) {
    return {
        type: 'SET_CART',
        payload,
    };
}

export { addProduct, removeProduct, clearCart, setCart };


// function addProduct(payload) {
//     // payload phải có quantity
//     return {
//         type: 'ADD_PRODUCT',
//         payload: { ...payload, quantity: payload.quantity || 1 },
//     };
// }

// // Xóa 1 sản phẩm theo id
// function removeProductById(id) {
//     return {
//         type: 'REMOVE_PRODUCT_BY_ID',
//         payload: id,
//     };
// }

// // Xóa toàn bộ giỏ hàng
// function clearCart() {
//     return {
//         type: 'CLEAR_CART',
//     };
// }

// export { addProduct, removeProductById, clearCart };
