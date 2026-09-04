package com.example.serviceapiecommerce.dto.payment;

import com.example.serviceapiecommerce.entity.PaymentTransactionStatus;
import com.example.serviceapiecommerce.entity.PaymentTransactionType;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;

public record PaymentTransactionResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("transaction_type")
        PaymentTransactionType transactionType,

        @JsonProperty("status")
        PaymentTransactionStatus status,

        @JsonProperty("amount")
        BigDecimal amount,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("provider")
        String provider,

        @JsonProperty("gateway_transaction_id")
        String gatewayTransactionId,

        @JsonProperty("gateway_payment_id")
        String gatewayPaymentId,

        @JsonProperty("idempotency_key")
        String idempotencyKey,

        @JsonProperty("failure_code")
        String failureCode,

        @JsonProperty("failure_message")
        String failureMessage,

        @JsonProperty("processed_at")
        Instant processedAt,

        @JsonProperty("created_at")
        Instant createdAt
) {
}
