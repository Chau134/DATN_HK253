package com.example.serviceapiecommerce.dto.payment;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

public record PaymentRefundRequest(
        @JsonProperty("amount")
        @DecimalMin(value = "0.01")
        BigDecimal amount,

        @JsonProperty("idempotency_key")
        @Size(max = 100)
        String idempotencyKey,

        @JsonProperty("reason")
        @Size(max = 150)
        String reason,

        @JsonProperty("note")
        @Size(max = 2000)
        String note
) {
}
