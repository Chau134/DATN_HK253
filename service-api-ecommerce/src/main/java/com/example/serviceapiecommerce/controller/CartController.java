package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.cart.CartItemAddRequest;
import com.example.serviceapiecommerce.dto.cart.CartItemUpdateRequest;
import com.example.serviceapiecommerce.dto.cart.CartResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.CartService;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/cart")
public class CartController {
    private final CartService cartService;

    public CartController(CartService cartService) {
        this.cartService = cartService;
    }

    @GetMapping
    public CartResponse cart(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return cartService.getCart(currentUser.id());
    }

    @PostMapping("/items")
    public CartResponse addItem(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody CartItemAddRequest request
    ) {
        return cartService.addItem(currentUser.id(), request);
    }

    @PatchMapping("/items/{cartItemId}")
    public CartResponse updateItem(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long cartItemId,
            @Valid @RequestBody CartItemUpdateRequest request
    ) {
        return cartService.updateItem(currentUser.id(), cartItemId, request);
    }

    @DeleteMapping("/items/{cartItemId}")
    public CartResponse removeItem(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long cartItemId
    ) {
        return cartService.removeItem(currentUser.id(), cartItemId);
    }
}
