package com.example.serviceapiecommerce.dto.order;

import com.example.serviceapiecommerce.entity.OrderStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record OrderStatusHistoryResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("from_status")
        OrderStatus fromStatus,

        @JsonProperty("to_status")
        OrderStatus toStatus,

        @JsonProperty("reason")
        String reason,

        @JsonProperty("note")
        String note,

        @JsonProperty("created_at")
        Instant createdAt
) {
}
