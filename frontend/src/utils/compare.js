import { titleOf } from './productDisplay';

const STORAGE_KEY = 'compareProducts';
const MAX_COMPARE = 4;
const EVENT_NAME = 'compare-updated';

export function getCompareList() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const list = raw ? JSON.parse(raw) : [];
        return Array.isArray(list) ? list : [];
    } catch {
        return [];
    }
}

function persist(list) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    window.dispatchEvent(new CustomEvent(EVENT_NAME));
}

export function isInCompare(productId) {
    return getCompareList().some((item) => String(item.id) === String(productId));
}

export function addToCompare(product) {
    const list = getCompareList();
    if (list.some((item) => String(item.id) === String(product.id))) {
        return { ok: true, list };
    }
    if (list.length >= MAX_COMPARE) {
        return { ok: false, reason: 'max', list };
    }
    const next = [...list, {
        id: product.id,
        nameProducts: titleOf(product),
        img: product.img,
        priceNew: product.priceNew,
    }];
    persist(next);
    return { ok: true, list: next };
}

export function removeFromCompare(productId) {
    const next = getCompareList().filter((item) => String(item.id) !== String(productId));
    persist(next);
    return next;
}

export function clearCompare() {
    persist([]);
}

export { MAX_COMPARE, EVENT_NAME };
