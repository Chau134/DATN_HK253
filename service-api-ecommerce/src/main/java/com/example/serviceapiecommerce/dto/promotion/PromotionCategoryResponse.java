package com.example.serviceapiecommerce.dto.promotion;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record PromotionCategoryResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("promotion_id")
        Long promotionId,

        @JsonProperty("category_id")
        Long categoryId,

        @JsonProperty("category_name")
        String categoryName,

        @JsonProperty("active")
        Boolean active,

        @JsonProperty("created_at")
        Instant createdAt
) {
}
