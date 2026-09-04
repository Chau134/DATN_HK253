package com.example.serviceapiecommerce.dto.order;

import com.example.serviceapiecommerce.entity.PaymentMethod;
import com.example.serviceapiecommerce.entity.PaymentStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;

public record OrderPaymentSummaryResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("payment_number")
        String paymentNumber,

        @JsonProperty("method")
        PaymentMethod method,

        @JsonProperty("status")
        PaymentStatus status,

        @JsonProperty("amount")
        BigDecimal amount,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("requested_at")
        Instant requestedAt,

        @JsonProperty("paid_at")
        Instant paidAt
) {
}
