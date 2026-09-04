package com.example.serviceapiecommerce.dto.wishlist;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record WishlistItemRequest(
        @JsonProperty("product_id")
        @NotNull
        Long productId,

        @JsonProperty("product_variant_id")
        Long productVariantId,

        @JsonProperty("note")
        @Size(max = 2000)
        String note
) {
}
