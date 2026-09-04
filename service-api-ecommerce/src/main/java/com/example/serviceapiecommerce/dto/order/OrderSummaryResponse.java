package com.example.serviceapiecommerce.dto.order;

import com.example.serviceapiecommerce.entity.OrderStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;

public record OrderSummaryResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("order_number")
        String orderNumber,

        @JsonProperty("status")
        OrderStatus status,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("item_count")
        Integer itemCount,

        @JsonProperty("total_amount")
        BigDecimal totalAmount,

        @JsonProperty("latest_payment")
        OrderPaymentSummaryResponse latestPayment,

        @JsonProperty("placed_at")
        Instant placedAt,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt,

        @JsonProperty("is_reviewed")
        Boolean isReviewed
) {
}
