export function stockNumber(value) {
    const stock = Number(value ?? 0);
    return Number.isFinite(stock) ? Math.max(stock, 0) : 0;
}

export function isVariantPurchasable(variant) {
    return Boolean(variant) && variant.available !== false && variant.active !== false && stockNumber(variant.inventory_count) > 0;
}

export function pickPurchasableVariant(product) {
    const variants = product?.variants || [];
    return variants.find(isVariantPurchasable) || variants[0] || null;
}

export function productStock(product, variant = null) {
    if (variant) return stockNumber(variant.inventory_count);
    return stockNumber(product?.total_stock ?? product?.quantityPro);
}

export function isProductPurchasable(product, variant = null) {
    if (!product || product.available === false) return false;
    if (variant) return isVariantPurchasable(variant);
    return productStock(product) > 0;
}

export function cartQuantityForProduct(cartItems, productId) {
    return (cartItems || [])
        .filter((item) => String(item?.id) === String(productId))
        .reduce((sum, item) => sum + stockNumber(item?.quantity || 1), 0);
}
