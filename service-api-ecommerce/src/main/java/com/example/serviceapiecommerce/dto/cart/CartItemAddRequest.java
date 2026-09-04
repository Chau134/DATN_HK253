package com.example.serviceapiecommerce.dto.cart;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

public record CartItemAddRequest(
        @JsonProperty("product_variant_id")
        @NotNull
        Long productVariantId,

        @JsonProperty("quantity")
        @NotNull
        @Min(1)
        @Max(999)
        Integer quantity
) {
}
