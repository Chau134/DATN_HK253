package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.wishlist.WishlistCreateRequest;
import com.example.serviceapiecommerce.dto.wishlist.WishlistItemRequest;
import com.example.serviceapiecommerce.dto.wishlist.WishlistResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.WishlistService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/wishlists")
public class WishlistController {
    private final WishlistService wishlistService;

    public WishlistController(WishlistService wishlistService) {
        this.wishlistService = wishlistService;
    }

    @GetMapping
    public List<WishlistResponse> wishlists(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return wishlistService.listWishlists(currentUser.id());
    }

    @GetMapping("/default")
    public WishlistResponse defaultWishlist(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return wishlistService.getDefaultWishlist(currentUser.id());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public WishlistResponse createWishlist(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody WishlistCreateRequest request
    ) {
        return wishlistService.createWishlist(currentUser.id(), request);
    }

    @PostMapping("/default/items")
    public WishlistResponse addDefaultWishlistItem(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody WishlistItemRequest request
    ) {
        return wishlistService.addItemToDefaultWishlist(currentUser.id(), request);
    }

    @PostMapping("/{wishlistId}/items")
    public WishlistResponse addWishlistItem(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long wishlistId,
            @Valid @RequestBody WishlistItemRequest request
    ) {
        return wishlistService.addItem(currentUser.id(), wishlistId, request);
    }

    @DeleteMapping("/items/{wishlistItemId}")
    public WishlistResponse removeWishlistItem(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long wishlistItemId
    ) {
        return wishlistService.removeItem(currentUser.id(), wishlistItemId);
    }

    @DeleteMapping("/default/items/products/{productId}")
    public WishlistResponse removeDefaultWishlistProduct(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long productId
    ) {
        return wishlistService.removeProductFromDefaultWishlist(currentUser.id(), productId);
    }

    @DeleteMapping("/{wishlistId}/items/products/{productId}")
    public WishlistResponse removeWishlistProduct(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long wishlistId,
            @PathVariable Long productId
    ) {
        return wishlistService.removeProduct(currentUser.id(), wishlistId, productId);
    }
}
