package com.example.serviceapiecommerce.dto.payment;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record CreateCodPaymentRequest(
        @JsonProperty("order_id")
        @NotNull
        Long orderId,

        @JsonProperty("idempotency_key")
        @Size(max = 100)
        String idempotencyKey,

        @JsonProperty("note")
        @Size(max = 2000)
        String note
) {
}
