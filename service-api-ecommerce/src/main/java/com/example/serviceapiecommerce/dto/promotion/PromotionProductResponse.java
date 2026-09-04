package com.example.serviceapiecommerce.dto.promotion;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record PromotionProductResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("promotion_id")
        Long promotionId,

        @JsonProperty("product_id")
        Long productId,

        @JsonProperty("product_title")
        String productTitle,

        @JsonProperty("active")
        Boolean active,

        @JsonProperty("created_at")
        Instant createdAt
) {
}
