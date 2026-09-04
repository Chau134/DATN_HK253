import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { loginSuccess } from '../../redux/authSlice';
import styles from './OAuth2Callback.module.scss';

function decodeBase64Url(value) {
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
    return decodeURIComponent(
        Array.from(atob(padded))
            .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, '0')}`)
            .join(''),
    );
}

function OAuth2Callback() {
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    useEffect(() => {
        const error = searchParams.get('oauth2_error');
        if (error) {
            navigate('/login', { replace: true, state: { oauth2Error: error } });
            return;
        }

        const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        const userPayload = params.get('user');

        if (!accessToken || !refreshToken || !userPayload) {
            navigate('/login', { replace: true, state: { oauth2Error: 'google_login_failed' } });
            return;
        }

        try {
            const user = JSON.parse(decodeBase64Url(userPayload));
            const roles = user?.roles || [];
            const role = roles.includes('ADMIN') ? 'admin' : 'user';
            dispatch(
                loginSuccess({
                    role,
                    user,
                    accessToken,
                    refreshToken,
                }),
            );
            navigate(role === 'admin' ? '/admin' : '/', { replace: true });
        } catch {
            navigate('/login', { replace: true, state: { oauth2Error: 'google_login_failed' } });
        }
    }, [dispatch, navigate, searchParams]);

    return (
        <main className={styles.wrapper}>
            <div className={styles.panel}>
                <h1>Dang nhap Google</h1>
                <p>Dang hoan tat phien dang nhap...</p>
            </div>
        </main>
    );
}

export default OAuth2Callback;
