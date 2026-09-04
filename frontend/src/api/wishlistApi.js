import request from '../config/Connect';

export async function fetchDefaultWishlist() {
    const response = await request.get('/api/wishlists/default');
    return response.data || null;
}

export async function addProductToDefaultWishlist(productId, productVariantId = null) {
    const response = await request.post('/api/wishlists/default/items', {
        product_id: productId,
        product_variant_id: productVariantId,
    });
    notifyWishlistChanged(response.data);
    return response.data || null;
}

export async function removeProductFromDefaultWishlist(productId) {
    const response = await request.delete(`/api/wishlists/default/items/products/${productId}`);
    notifyWishlistChanged(response.data);
    return response.data || null;
}

export function productIdsFromWishlist(wishlist) {
    return new Set((wishlist?.items || []).map((item) => Number(item.product_id ?? item.productId)).filter(Boolean));
}

function notifyWishlistChanged(wishlist) {
    window.dispatchEvent(new CustomEvent('wishlist:changed', {
        detail: {
            itemCount: wishlist?.item_count ?? wishlist?.itemCount ?? wishlist?.items?.length ?? 0,
        },
    }));
}
