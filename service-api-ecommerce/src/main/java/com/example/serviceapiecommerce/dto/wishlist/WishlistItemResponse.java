package com.example.serviceapiecommerce.dto.wishlist;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record WishlistItemResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("product_id")
        Long productId,

        @JsonProperty("product_variant_id")
        Long productVariantId,

        @JsonProperty("product_name")
        String productName,

        @JsonProperty("product_name_vi")
        String productNameVi,

        @JsonProperty("brand_name")
        String brandName,

        @JsonProperty("image_url")
        String imageUrl,

        @JsonProperty("note")
        String note,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
