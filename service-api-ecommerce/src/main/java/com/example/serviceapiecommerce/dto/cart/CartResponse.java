package com.example.serviceapiecommerce.dto.cart;

import com.example.serviceapiecommerce.entity.CartStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record CartResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("status")
        CartStatus status,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("item_count")
        Integer itemCount,

        @JsonProperty("total_quantity")
        Integer totalQuantity,

        @JsonProperty("subtotal")
        BigDecimal subtotal,

        @JsonProperty("items")
        List<CartItemResponse> items,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
