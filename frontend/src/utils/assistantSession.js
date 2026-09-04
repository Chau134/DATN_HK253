const ASSISTANT_SESSION_KEY = 'mystery_closet_assistant_session_id';
const ASSISTANT_USER_KEY = 'mystery_closet_assistant_user_id';

function createSessionId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `web-chat-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function getAssistantSessionId() {
    const existing = window.sessionStorage.getItem(ASSISTANT_SESSION_KEY);
    if (existing) return existing;

    const sessionId = createSessionId();
    window.sessionStorage.setItem(ASSISTANT_SESSION_KEY, sessionId);
    return sessionId;
}

export function resetAssistantSessionId() {
    const sessionId = createSessionId();
    window.sessionStorage.setItem(ASSISTANT_SESSION_KEY, sessionId);
    return sessionId;
}

export function getAssistantUserId() {
    const existing = window.localStorage.getItem(ASSISTANT_USER_KEY);
    if (existing) return existing;

    const userId = createSessionId();
    window.localStorage.setItem(ASSISTANT_USER_KEY, userId);
    return userId;
}
