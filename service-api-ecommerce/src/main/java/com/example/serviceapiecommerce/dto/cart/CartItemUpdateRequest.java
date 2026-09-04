package com.example.serviceapiecommerce.dto.cart;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

public record CartItemUpdateRequest(
        @JsonProperty("quantity")
        @Min(1)
        @Max(999)
        Integer quantity,

        @JsonProperty("selected")
        Boolean selected
) {
}
