package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record AdminProductImageResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("product_id")
        Long productId,

        @JsonProperty("image_type")
        String imageType,

        @JsonProperty("image_url")
        String imageUrl,

        @JsonProperty("sort_order")
        Integer sortOrder,

        @JsonProperty("created_at")
        Instant createdAt
) {
}
