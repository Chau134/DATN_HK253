import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/spring-api';
const AUTH_STORAGE_KEY = 'client_auth';

function readAuthState() {
    try {
        return JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || '{}');
    } catch {
        return {};
    }
}

function writeAuthState(nextState) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextState));
}

const request = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

request.interceptors.request.use((config) => {
    if (config.data instanceof FormData) {
        delete config.headers['Content-Type'];
        delete config.headers['content-type'];
    }

    const token = readAuthState().accessToken;
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

request.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        const authState = readAuthState();

        if (
            error.response?.status === 401 &&
            originalRequest &&
            !originalRequest._retry &&
            authState.refreshToken &&
            !originalRequest.url?.includes('/api/auth/login') &&
            !originalRequest.url?.includes('/api/auth/refresh')
        ) {
            originalRequest._retry = true;
            try {
                const refreshResponse = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
                    refresh_token: authState.refreshToken,
                });
                const nextAuthState = {
                    ...authState,
                    user: refreshResponse.data?.user || authState.user,
                    accessToken: refreshResponse.data?.access_token,
                    refreshToken: refreshResponse.data?.refresh_token || authState.refreshToken,
                };
                writeAuthState(nextAuthState);
                originalRequest.headers.Authorization = `Bearer ${nextAuthState.accessToken}`;
                return request(originalRequest);
            } catch {
                localStorage.removeItem(AUTH_STORAGE_KEY);
            }
        } else if (error.response?.status === 401) {
            localStorage.removeItem(AUTH_STORAGE_KEY);
        }
        return Promise.reject(error);
    },
);

export function getApiError(error, fallback = 'Yêu cầu thất bại') {
    const data = error?.response?.data;
    if (!data) return error?.message || fallback;
    if (typeof data === 'string') return data || fallback;
    if (data.field_errors?.length) {
        return data.field_errors.map((item) => `${item.field}: ${item.message}`).join(', ');
    }
    return data.message || data.error || fallback;
}

export { AUTH_STORAGE_KEY };
export default request;
