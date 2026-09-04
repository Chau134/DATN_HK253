import { titleOf } from './productDisplay';

const STORAGE_KEY = 'recentlyViewed';
const MAX_ITEMS = 10;
const EVENT_NAME = 'recently-viewed-updated';

export function getRecentlyViewed() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const list = raw ? JSON.parse(raw) : [];
        return Array.isArray(list) ? list : [];
    } catch {
        return [];
    }
}

export function addRecentlyViewed(product) {
    if (!product?.id) return;

    const entry = {
        id: product.id,
        nameProducts: titleOf(product),
        img: product.img,
        priceNew: product.priceNew,
    };

    const existing = getRecentlyViewed().filter((item) => String(item.id) !== String(product.id));
    const next = [entry, ...existing].slice(0, MAX_ITEMS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent(EVENT_NAME));
}

export function clearRecentlyViewed() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([]));
    window.dispatchEvent(new CustomEvent(EVENT_NAME));
}

export { MAX_ITEMS, EVENT_NAME };
