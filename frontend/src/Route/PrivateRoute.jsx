import React from 'react';
import { Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';

function PrivateRoute({ children }) {
    const { isAuthenticated, role } = useSelector((state) => state.auth);
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }
    if (role !== 'admin') {
        return <Navigate to="/" replace />;
    }

    return children;
}

export default PrivateRoute;
