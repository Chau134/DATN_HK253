export function formatProductName(value, fallback = 'Sản phẩm') {
    const name = typeof value === 'string' ? value.trim().replace(/\s+/g, ' ') : '';
    if (!name) return fallback;

    const normalized = name === name.toLocaleUpperCase('vi-VN')
        ? name.toLocaleLowerCase('vi-VN')
        : name;

    return normalized.charAt(0).toLocaleUpperCase('vi-VN') + normalized.slice(1);
}

export function titleOf(product, fallback = 'Sản phẩm') {
    const title =
        product?.title_vi ||
        product?.product_name_vi ||
        product?.productTitleVi ||
        product?.product_title_vi ||
        product?.title ||
        product?.product_name ||
        product?.productTitle ||
        product?.product_title ||
        product?.nameProducts ||
        product?.nameProduct;

    return formatProductName(title, fallback);
}

export function descriptionOf(product, fallback = 'Chưa có mô tả sản phẩm.') {
    return product?.description_vi || product?.description || product?.des || fallback;
}
