import React from 'react';
import ReactDOM from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'slick-carousel/slick/slick.css';
import 'slick-carousel/slick/slick-theme.css';
import reportWebVitals from './reportWebVitals';
import { privateRoute, publicRoutes } from './Route';
import ChatBot from './ultils/ChatBot/ChatBot';

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import store from './redux/store';

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
    <React.StrictMode>
        <Provider store={store}>
            <Router>
                <Routes>
                    {publicRoutes.map((route, index) => (
                        <Route key={index} path={route.path} element={route.element} />
                    ))}

                    {privateRoute.map((route, index) => (
                        <Route key={index} path={route.path} element={route.element} />
                    ))}
                </Routes>
                <ChatBot />
            </Router>
        </Provider>
    </React.StrictMode>,
);

reportWebVitals();
