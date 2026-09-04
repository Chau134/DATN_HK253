package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.wishlist.WishlistCreateRequest;
import com.example.serviceapiecommerce.dto.wishlist.WishlistItemRequest;
import com.example.serviceapiecommerce.dto.wishlist.WishlistResponse;
import java.util.List;

public interface WishlistService {
    List<WishlistResponse> listWishlists(Long userAccountId);

    WishlistResponse getDefaultWishlist(Long userAccountId);

    WishlistResponse createWishlist(Long userAccountId, WishlistCreateRequest request);

    WishlistResponse addItemToDefaultWishlist(Long userAccountId, WishlistItemRequest request);

    WishlistResponse addItem(Long userAccountId, Long wishlistId, WishlistItemRequest request);

    WishlistResponse removeItem(Long userAccountId, Long wishlistItemId);

    WishlistResponse removeProductFromDefaultWishlist(Long userAccountId, Long productId);

    WishlistResponse removeProduct(Long userAccountId, Long wishlistId, Long productId);
}
