package com.example.serviceapiecommerce.dto.wishlist;

import com.example.serviceapiecommerce.entity.WishlistStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

public record WishlistResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("name")
        String name,

        @JsonProperty("default_wishlist")
        Boolean defaultWishlist,

        @JsonProperty("status")
        WishlistStatus status,

        @JsonProperty("item_count")
        Integer itemCount,

        @JsonProperty("items")
        List<WishlistItemResponse> items,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
