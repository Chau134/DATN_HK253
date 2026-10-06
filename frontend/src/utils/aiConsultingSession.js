const EMPTY_SESSION = {
    textQuery: '',
    imageOnly: null,
    hybridQuery: '',
    hybridImage: null,
    searchResult: null,
    error: '',
};

// Keep the current consulting session alive while the SPA is running. Images are
// intentionally not written to sessionStorage because their base64 payload can
// easily exceed browser storage limits.
let consultingSession = { ...EMPTY_SESSION };

export function readAiConsultingSession() {
    return consultingSession;
}

export function writeAiConsultingSession(session) {
    consultingSession = { ...session };
}
