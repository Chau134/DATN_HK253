package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.cart.CartItemAddRequest;
import com.example.serviceapiecommerce.dto.cart.CartItemUpdateRequest;
import com.example.serviceapiecommerce.dto.cart.CartResponse;

public interface CartService {
    CartResponse getCart(Long userAccountId);

    CartResponse addItem(Long userAccountId, CartItemAddRequest request);

    CartResponse updateItem(Long userAccountId, Long cartItemId, CartItemUpdateRequest request);

    CartResponse removeItem(Long userAccountId, Long cartItemId);
}
