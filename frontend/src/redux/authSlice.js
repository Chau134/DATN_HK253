import { createSlice } from '@reduxjs/toolkit';
import { AUTH_STORAGE_KEY } from '../config/Connect';

function loadAuthState() {
    try {
        const saved = JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || '{}');
        if (saved?.accessToken && saved?.role) {
            return {
                isAuthenticated: true,
                role: saved.role,
                user: saved.user || null,
                accessToken: saved.accessToken,
                refreshToken: saved.refreshToken || null,
            };
        }
    } catch {
        localStorage.removeItem(AUTH_STORAGE_KEY);
    }

    return {
        isAuthenticated: false,
        role: null,
        user: null,
        accessToken: null,
        refreshToken: null,
    };
}

const initialState = loadAuthState();

function persistAuth(state) {
    localStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({
            role: state.role,
            user: state.user,
            accessToken: state.accessToken,
            refreshToken: state.refreshToken,
        }),
    );
}

const authSlice = createSlice({
    name: 'auth',
    initialState,
    reducers: {
        loginSuccess: (state, action) => {
            state.isAuthenticated = true;
            state.role = action.payload.role;
            state.user = action.payload.user || null;
            state.accessToken = action.payload.accessToken || action.payload.access_token || null;
            state.refreshToken = action.payload.refreshToken || action.payload.refresh_token || null;
            persistAuth(state);
        },
        logout: (state) => {
            state.isAuthenticated = false;
            state.role = null;
            state.user = null;
            state.accessToken = null;
            state.refreshToken = null;
            localStorage.removeItem(AUTH_STORAGE_KEY);
        },
    },
});

export const { loginSuccess, logout } = authSlice.actions;
export default authSlice.reducer;
