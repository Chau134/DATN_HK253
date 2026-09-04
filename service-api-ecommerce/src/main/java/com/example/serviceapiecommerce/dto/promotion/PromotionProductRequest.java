package com.example.serviceapiecommerce.dto.promotion;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;

public record PromotionProductRequest(
        @JsonProperty("product_id")
        @NotNull
        Long productId,

        @JsonProperty("active")
        Boolean active
) {
}
