// const initState = localStorage.getItem('products') ? JSON.parse(localStorage.getItem('products')) : [];
// khởi tạo giá trị ban đầu từ local storage. lấy giá trị của product từ local Storage? chuyển đổi chuỗi Json lấy từ LocalStorage thành JVScrip.
// Nếu localStorage không có key product thì init State sẽ là 1 mảng rỗng
// function reducerUser(state = initState, action) {
//     // Gán state ban đầu là initState, action là hành động gửi đến reducer
//     switch (
//         action.type // Khi thay đổi action.type thì thay đổi state
//     ) {
//         case 'ADD_PRODUCT': // xử lý action 'ADD_PRODUCT'
//             const existingProductIndex = state.findIndex((product) => product.id === action.payload.id); // tìm Id sp có  trùng với Id của sp trong cart
//             if (existingProductIndex === -1) {
//                 // nếu sp ko tồn tại trong cart
//                 const updatedState = [...state, action.payload]; // tạo mảng updatedState sẽ là state + action.payload. Thêm sản phẩm mới vào cart
//                 localStorage.setItem('products', JSON.stringify(updatedState)); //cập nhật localStorage với updatedState
//                 return updatedState; //trả về updatedState
//             } else {
//                 const updatedState = [...state]; // mảng updatedState sẽ là state
//                 updatedState[existingProductIndex] = {
//                     ...updatedState[existingProductIndex], // cập nhật mảng updatedState với updatedState[existingProductIndex] (sẽ là state)
//                     quantity: updatedState[existingProductIndex].quantity + action.payload.quantity, // cập nhật số lượng của sp
//                 };
//                 localStorage.setItem('products', JSON.stringify(updatedState));
//                 return updatedState; // trả về trạng thái updatedState là state
//             }
//         case 'REMOVE_PRODUCT': // xử lý action 'REMOVE_PRODUCT'
//             const updatedState = []; // lọc với updatedState
//             localStorage.setItem('products', JSON.stringify(updatedState)); // cập nhật localStorage với updatedState
//             return updatedState; //trả về updatedState
//         default: // khi thay đổi action.type thì thay đổi state
//             return state; // trả về state
//     }
// }

// export default reducerUser;


function readCartFromStorage() {
    try {
        const storedCart = JSON.parse(localStorage.getItem('products') || '[]');
        return Array.isArray(storedCart) ? storedCart : [];
    } catch {
        localStorage.removeItem('products');
        return [];
    }
}

const initState = readCartFromStorage();

function reducerUser(state = initState, action) {
    switch (action.type) {
        case 'ADD_PRODUCT': {
            const index = state.findIndex(p => p.id === action.payload.id);
            let updatedState;
            if (index === -1) {
                updatedState = [...state, { ...action.payload, quantity: action.payload.quantity || 1 }];
            } else {
                updatedState = [...state];
                updatedState[index] = {
                    ...updatedState[index],
                    quantity: (updatedState[index].quantity || 1) + (action.payload.quantity || 1)
                };
            }
            localStorage.setItem('products', JSON.stringify(updatedState));
            return updatedState;
        }

        case 'REMOVE_PRODUCT': {
            const updatedState = state.filter(p => p.id !== action.payload);
            localStorage.setItem('products', JSON.stringify(updatedState));
            return updatedState;
        }

        case 'CLEAR_CART': {
            localStorage.setItem('products', JSON.stringify([]));
            return [];
        }

        case 'SET_CART': {
            const updatedState = action.payload || [];
            localStorage.setItem('products', JSON.stringify(updatedState));
            return updatedState;
        }

        default:
            return state;
    }
}

export default reducerUser;
