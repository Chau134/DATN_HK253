import axios from 'axios';
import { resolveImageUrl } from '../utils/image';
import { descriptionOf, titleOf } from '../utils/productDisplay';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/spring-api';

const catalogRequest = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

function productPrice(product) {
    return Number(
        product?.price?.effective_price ??
            product?.price?.discounted_price ??
            product?.price?.price ??
            product?.effective_price ??
            product?.priceNew ??
            0,
    );
}

function addImageUrl(urls, value) {
    if (!value || typeof value !== 'string') return;
    const trimmed = value.trim();
    if (trimmed && !urls.includes(trimmed)) {
        urls.push(trimmed);
    }
}

function collectProductImageUrls(product) {
    const urls = [];

    addImageUrl(urls, product?.main_image || product?.mainImage);
    addImageUrl(urls, product?.image_url || product?.imageUrl);

    const imageUrls = product?.image_urls || product?.imageUrls;
    if (Array.isArray(imageUrls)) {
        imageUrls.forEach((url) => addImageUrl(urls, url));
    }

    if (Array.isArray(product?.images)) {
        product.images.forEach((image) => {
            addImageUrl(urls, image?.image_url || image?.imageUrl || image?.url);
        });
    }

    addImageUrl(urls, product?.img);

    return urls;
}

export function normalizeCatalogProduct(product) {
    const imageUrls = collectProductImageUrls(product);
    const image = resolveImageUrl(imageUrls[0] || '');
    const title = titleOf(product);
    const stock = product?.total_stock ?? product?.quantityPro ?? (product?.available === false ? 0 : 1);

    return {
        ...product,
        _id: product?.id,
        id: product?.id,
        image_urls: imageUrls,
        nameProducts: title,
        img: image,
        priceNew: productPrice(product),
        quantityPro: stock,
        author: product?.brand || product?.gender_vi || product?.gender || '',
        des: descriptionOf(product, title),
        rawProduct: product,
    };
}

export async function fetchCatalogProducts(params = {}) {
    const response = await catalogRequest.get('/api/products', { params });
    const pageData = response.data || {};
    const items = Array.isArray(pageData.items) ? pageData.items : Array.isArray(pageData) ? pageData : [];

    return {
        ...pageData,
        items: items.map(normalizeCatalogProduct),
    };
}

export async function fetchCatalogProduct(productId) {
    const response = await catalogRequest.get(`/api/products/${productId}`);
    return normalizeCatalogProduct(response.data || {});
}

export async function fetchCatalogProductReviews(productId) {
    const response = await catalogRequest.get(`/api/products/${productId}/reviews`);
    return Array.isArray(response.data) ? response.data : [];
}

export async function fetchCatalogProductReviewSummary(productId) {
    const response = await catalogRequest.get(`/api/products/${productId}/reviews/summary`);
    return response.data || null;
}

export async function fetchRecentReviews(limit = 6) {
    const response = await catalogRequest.get('/api/reviews/recent', { params: { limit } });
    return Array.isArray(response.data) ? response.data : [];
}

export async function fetchCatalogCategories() {
    const response = await catalogRequest.get('/api/categories');
    return Array.isArray(response.data) ? response.data : [];
}

export async function fetchCatalogPromotions() {
    const response = await catalogRequest.get('/api/promotions');
    return Array.isArray(response.data) ? response.data : [];
}

export async function fetchCatalogBrands() {
    const response = await catalogRequest.get('/api/brands');
    return Array.isArray(response.data) ? response.data : [];
}
