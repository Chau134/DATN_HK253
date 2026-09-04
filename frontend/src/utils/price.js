const DB_PRICE_DISPLAY_MULTIPLIER = 1;

export function priceToDisplayValue(value) {
    const numericValue = Number(value || 0);
    return Number.isFinite(numericValue) ? numericValue * DB_PRICE_DISPLAY_MULTIPLIER : 0;
}

export function formatVndFromDb(value) {
    return `${priceToDisplayValue(value).toLocaleString('vi-VN')} VNĐ`;
}

export function formatCurrencyFromDb(value, currency = 'VND') {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency,
        maximumFractionDigits: 0,
    }).format(priceToDisplayValue(value));
}
