import request from '../config/Connect';

export const aiApi = {
    textSearch: (payload) => request.post('/api/search/ai/text', payload).then((res) => res.data),
    autoSearch: (payload) => request.post('/api/search/ai/auto', payload).then((res) => res.data),
    imageSearch: (payload) => request.post('/api/search/ai/image', payload).then((res) => res.data),
    detectImage: (payload) => request.post('/api/search/ai/image/detections', payload).then((res) => res.data),
    hybridSearch: (payload) => request.post('/api/search/ai/hybrid', payload).then((res) => res.data),
    assistant: (payload) => request.post('/api/assistant/chat', payload).then((res) => res.data),
    assistantFeedback: (payload) => request.post('/api/assistant/feedback', payload).then((res) => res.data),
};

export function getApiError(error) {
    const data = error?.response?.data;
    if (!data) {
        if (error?.code === 'ERR_NETWORK') {
            return 'Không kết nối được API. Hãy kiểm tra service-api-ecommerce đang chạy và khởi động lại npm run dev để nhận proxy mới.';
        }
        return error?.message || 'Không kết nối được API';
    }
    if (typeof data === 'string') {
        return data || 'Yêu cầu thất bại';
    }
    if (data.field_errors?.length) {
        return data.field_errors.map((item) => `${item.field}: ${item.message}`).join(', ');
    }
    if (data.detail) {
        if (Array.isArray(data.detail)) {
            return data.detail.map((item) => item.msg || item.message || JSON.stringify(item)).join(', ');
        }
        return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
    return data.message || data.error || 'Yêu cầu thất bại';
}

const INTERNAL_AI_WARNINGS = new Set([
    'llm_reply_fallback',
    'llm_reply_grounding_validation_failed',
]);

export function formatAiWarning(warning) {
    const warningMap = {
        ai_service_disabled: 'Dịch vụ AI đang tắt.',
        ai_service_mock_enabled: 'Dịch vụ AI đang chạy chế độ mô phỏng.',
        ai_service_unavailable: 'Dịch vụ AI chưa sẵn sàng hoặc đang mất kết nối. Hãy kiểm tra service-ai.',
        ai_keyword_fallback: 'AI chưa phản hồi, hệ thống đã dùng tìm kiếm từ khóa thay thế.',
        no_search_results: 'Chưa tìm thấy sản phẩm khớp với yêu cầu.',
        search_recovery_used: 'Hệ thống đã mở rộng tìm kiếm để có thêm gợi ý.',
        search_recovery_exhausted: 'Đã thử mở rộng tìm kiếm nhưng vẫn chưa có kết quả phù hợp.',
        comparison_leg_unresolved: 'Chưa tìm được một trong hai sản phẩm để so sánh.',
        spring_boot_unavailable: 'Dịch vụ sản phẩm tạm gián đoạn, vui lòng thử lại sau.',
    };

    return warningMap[warning] || warning;
}

export function formatAiWarnings(warnings, separator = ' ') {
    return (warnings || [])
        .filter((warning) => !INTERNAL_AI_WARNINGS.has(warning))
        .map(formatAiWarning)
        .filter(Boolean)
        .join(separator);
}
