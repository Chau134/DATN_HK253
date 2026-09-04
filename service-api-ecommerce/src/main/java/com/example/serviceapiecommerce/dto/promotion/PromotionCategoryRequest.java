package com.example.serviceapiecommerce.dto.promotion;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;

public record PromotionCategoryRequest(
        @JsonProperty("category_id")
        @NotNull
        Long categoryId,

        @JsonProperty("active")
        Boolean active
) {
}
