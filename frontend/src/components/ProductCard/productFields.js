export { titleOf } from '../../utils/productDisplay';

export function productIdOf(product) {
    return product?.id || product?.product_id;
}

export function priceOf(product) {
    return product?.price?.effective_price ?? product?.effective_price ?? product?.price?.price ?? product?.price ?? product?.priceNew ?? 0;
}

export function currencyOf(product) {
    return product?.price?.currency || product?.currency || 'VND';
}
