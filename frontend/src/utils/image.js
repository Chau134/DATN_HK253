import fallbackProductImage from '../Pages/Layouts/HomePage/img/latest1.jpg';

export const PRODUCT_IMAGE_FALLBACK = fallbackProductImage;

export function isUsableImageUrl(value) {
    if (!value || typeof value !== 'string') return false;

    const trimmed = value.trim();
    if (!trimmed) return false;

    try {
        const parsedUrl = new URL(trimmed, window.location.origin);
        const hostname = parsedUrl.hostname.toLowerCase();
        return hostname !== 'cdn.test' && !hostname.endsWith('.test');
    } catch {
        return false;
    }
}

export function resolveImageUrl(value, fallback = PRODUCT_IMAGE_FALLBACK) {
    return isUsableImageUrl(value) ? value.trim() : fallback;
}

export function handleImageFallback(event, fallback = PRODUCT_IMAGE_FALLBACK) {
    if (!event?.currentTarget || event.currentTarget.src === fallback) return;
    event.currentTarget.src = fallback;
}
