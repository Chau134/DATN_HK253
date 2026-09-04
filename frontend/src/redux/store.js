// import { legacy_createStore as createStore } from 'redux'; // import thu vien
// import reducerUser from './reducer'; // import reducer

// const store = createStore(reducerUser); // tạo store tuong ung voi createStore. reducerUser để quản lý trạng thái thông qua reducer

// export default store; // export store

import { configureStore } from '@reduxjs/toolkit';
import authReducer from './authSlice';
import reducerUser from './reducer'
const store = configureStore({
    reducer: {
        auth: authReducer,
        cart: reducerUser,
    },
});

export default store;
