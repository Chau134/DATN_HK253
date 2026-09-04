import request from '../config/Connect';
import { resolveImageUrl } from '../utils/image';
import { titleOf } from '../utils/productDisplay';

export function normalizeAdminCategory(category) {
    return {
        ...category,
        id: category?.id,
        label: category?.name_vi || category?.name || `Danh mục ${category?.id}`,
        value: String(category?.id),
        parent_id: category?.parent_id ? String(category.parent_id) : null,
    };
}

export function normalizeAdminProduct(product) {
    const firstPrice = product?.prices?.[0] || {};
    const firstVariant = product?.variants?.[0] || {};
    const mainImage = resolveImageUrl(product?.main_image || product?.images?.[0]?.image_url || '');
    const categoryId = product?.category_ids?.[0] ? String(product.category_ids[0]) : '';

    return {
        ...product,
        _id: product?.id,
        id: product?.id,
        nameProducts: titleOf(product),
        img: mainImage,
        priceNew: Number(firstPrice.selling_price ?? 0),
        sellingPrice: Number(firstPrice.selling_price ?? 0),
        importPrice: Number(firstPrice.import_price ?? 0),
        vat: Number(firstPrice.vat ?? 0),
        checkProducts: categoryId,
        checkType: product?.variant_name_vi || product?.variant_name || firstVariant.option_value || '',
        quantityPro: Number(firstVariant.inventory_count ?? 0),
    };
}

export function normalizeAdminOrder(order) {
    const latestPayment = order?.latest_payment || null;
    const status = order?.status || 'PENDING';
    const paymentStatus = latestPayment?.status || null;

    return {
        ...order,
        _id: order?.id,
        email: order?.customer_email || order?.email || order?.order_number || `Đơn #${order?.id}`,
        products: [
            {
                nameProduct: order?.order_number || `Đơn hàng ${order?.id}`,
            },
        ],
        latestPayment,
        paymentId: latestPayment?.id,
        status,
        statusOrder: ['DELIVERED', 'COMPLETED'].includes(status),
        statusPayment: paymentStatus === 'PAID',
        canConfirmCod:
            latestPayment?.method === 'COD' &&
            paymentStatus === 'PENDING' &&
            ['PENDING', 'CONFIRMED'].includes(status),
    };
}

export async function fetchAdminProducts() {
    const res = await request.get('/admin/catalog/products');
    return Array.isArray(res.data) ? res.data.map(normalizeAdminProduct) : [];
}

export async function fetchAdminCategories(params = { active: true }) {
    const res = await request.get('/admin/catalog/categories', { params });
    return Array.isArray(res.data) ? res.data.map(normalizeAdminCategory) : [];
}

export async function fetchAdminOrders() {
    const res = await request.get('/admin/orders');
    return Array.isArray(res.data) ? res.data.map(normalizeAdminOrder) : [];
}
