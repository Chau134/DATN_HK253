// import React from 'react';
// import App from '../App';
// import Loading from '../Layouts/Loading/Loading';
// import DefaultLayout from '../Pages/Admin/DefaultLayout/DefaultLayout';
// import Blogger from '../Pages/Blog/Aboutus';
// import CartUser from '../Pages/Cart/Cart';
// import Checkout from '../Pages/Checkout/Checkout';
// import Contact from '../Pages/Contact/Contact';
// import DefaultPage from '../Pages/DefaultPage/DefaultPage';
// import ForgotPassword from '../Pages/ForgotPassword/ForgotPassword';
// import InfoUser from '../Pages/InfoUser/InfoUser';
// import LoginUser from '../Pages/Login/LoginUser';
// import OrderHistory from '../Pages/OrderHistory/OrderHistory';
// import ProductDetail from '../Pages/ProductDetail/ProductDetail';
// import RegisterUser from '../Pages/Register/RegisterUser';
// import SuccessfulPaymentPage from '../Pages/SuccessfulPaymentPage/SuccessfulPaymentPage';
// import ReturnPolicy from '../Pages/Policy/ReturnPolicy/ReturnPolicy';
// import ShippingPolicy from '../Pages/Policy/ShippingPolicy/ShippingPolicy';
// import PrivacyPolicy from '../Pages/Policy/PrivacyPolicy/PrivacyPolicy';
// import TermsOfUse from '../Pages/Policy/TermsOfUse/TermsOfUse';
// import PurchaseGuide from '../Pages/Policy/PurchaseGuide/PurchaseGuide';

// export const publicRoutes = [
//     { path: '/', element: <App /> },
//     { path: '/category', element: <DefaultPage /> },
//     { path: '/login', element: <LoginUser /> },
//     { path: '/register', element: <RegisterUser /> },
//     { path: '/cart', element: <CartUser /> },
//     { path: '/checkout', element: <Checkout /> },
//     { path: '/prodetail/:id', element: <ProductDetail /> },
//     { path: '/loading', element: <Loading /> },
//     { path: '/info', element: <InfoUser /> },
//     { path: '/order-history', element: <OrderHistory /> },
//     { path: '/thanks', element: <SuccessfulPaymentPage /> },
//     { path: '/contact', element: <Contact /> },
//     { path: '/aboutus', element: <Blogger /> },
//     { path: '/forgot-password', element: <ForgotPassword /> },
//     { path: '/chinh-sach-doi-tra', element: <ReturnPolicy /> },
//     { path: '/chinh-sach-van-chuyen', element: <ShippingPolicy /> },
//     { path: '/chinh-sach-bao-mat', element: <PrivacyPolicy /> },
//     { path: '/dieu-khoan-su-dung', element: <TermsOfUse /> },
//     { path: '/huong-dan-mua-hang', element: <PurchaseGuide /> },
// ];

// export const privateRoute = [{ path: '/admin', element: <DefaultLayout /> }];

import React from 'react';
import App from '../App';
import Loading from '../Layouts/Loading/Loading';
import DefaultLayout from '../Pages/Admin/DefaultLayout/DefaultLayout';
import Blogger from '../Pages/Blog/Aboutus';
import BlogDetail from '../Pages/Blog/BlogDetail';
import CartUser from '../Pages/Cart/Cart';
import Checkout from '../Pages/Checkout/Checkout';
import Contact from '../Pages/Contact/Contact';
import DefaultPage from '../Pages/DefaultPage/DefaultPage';
import ProductComparison from '../Pages/ProductComparison/ProductComparison';
import VnpayReturn from '../Pages/VnpayReturn/VnpayReturn';
import AiConsulting from '../Pages/AiConsulting/AiConsulting';
import ForgotPassword from '../Pages/ForgotPassword/ForgotPassword';
import InfoUser from '../Pages/InfoUser/InfoUser';
import LoginUser from '../Pages/Login/LoginUser';
import OAuth2Callback from '../Pages/OAuth2Callback/OAuth2Callback';
import OrderHistory from '../Pages/OrderHistory/OrderHistory';
import ProductDetail from '../Pages/ProductDetail/ProductDetail';
import RegisterUser from '../Pages/Register/RegisterUser';
import SuccessfulPaymentPage from '../Pages/SuccessfulPaymentPage/SuccessfulPaymentPage';
import Wishlist from '../Pages/Wishlist/Wishlist';
import ReturnPolicy from '../Pages/Policy/ReturnPolicy/ReturnPolicy';
import ShippingPolicy from '../Pages/Policy/ShippingPolicy/ShippingPolicy';
import PrivacyPolicy from '../Pages/Policy/PrivacyPolicy/PrivacyPolicy';
import TermsOfUse from '../Pages/Policy/TermsOfUse/TermsOfUse';
import PurchaseGuide from '../Pages/Policy/PurchaseGuide/PurchaseGuide';

import PrivateRoute from './PrivateRoute';

export const publicRoutes = [
    { path: '/', element: <App /> },
    { path: '/category', element: <DefaultPage /> },
    { path: '/compare', element: <ProductComparison /> },
    { path: '/tu-van', element: <AiConsulting /> },
    { path: '/ai', element: <AiConsulting /> },
    { path: '/login', element: <LoginUser /> },
    { path: '/oauth2/callback', element: <OAuth2Callback /> },
    { path: '/register', element: <RegisterUser /> },
    { path: '/cart', element: <CartUser /> },
    { path: '/checkout', element: <Checkout /> },
    { path: '/prodetail/:id', element: <ProductDetail /> },
    { path: '/loading', element: <Loading /> },
    { path: '/info', element: <InfoUser /> },
    { path: '/wishlist', element: <Wishlist /> },
    { path: '/order-history', element: <OrderHistory /> },
    { path: '/thanks', element: <SuccessfulPaymentPage /> },
    { path: '/vnpay/return', element: <VnpayReturn /> },
    { path: '/contact', element: <Contact /> },
    { path: '/blog', element: <Blogger /> },
    { path: '/blog/:id', element: <BlogDetail /> },
    { path: '/aboutus', element: <Blogger /> },
    { path: '/forgot-password', element: <ForgotPassword /> },
    { path: '/chinh-sach-doi-tra', element: <ReturnPolicy /> },
    { path: '/chinh-sach-van-chuyen', element: <ShippingPolicy /> },
    { path: '/chinh-sach-bao-mat', element: <PrivacyPolicy /> },
    { path: '/dieu-khoan-su-dung', element: <TermsOfUse /> },
    { path: '/huong-dan-mua-hang', element: <PurchaseGuide /> },
];

export const privateRoute = [
    {
        path: '/admin',
        element: (
            <PrivateRoute>
                <DefaultLayout />
            </PrivateRoute>
        ),
    },
];
