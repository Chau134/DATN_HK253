package com.example.serviceapiecommerce.dto.payment;

import com.example.serviceapiecommerce.entity.PaymentMethod;
import com.example.serviceapiecommerce.entity.PaymentStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record PaymentResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("payment_number")
        String paymentNumber,

        @JsonProperty("order_id")
        Long orderId,

        @JsonProperty("order_number")
        String orderNumber,

        @JsonProperty("method")
        PaymentMethod method,

        @JsonProperty("status")
        PaymentStatus status,

        @JsonProperty("amount")
        BigDecimal amount,

        @JsonProperty("refunded_amount")
        BigDecimal refundedAmount,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("provider")
        String provider,

        @JsonProperty("gateway_payment_id")
        String gatewayPaymentId,

        @JsonProperty("gateway_order_id")
        String gatewayOrderId,

        @JsonProperty("idempotency_key")
        String idempotencyKey,

        @JsonProperty("requested_at")
        Instant requestedAt,

        @JsonProperty("paid_at")
        Instant paidAt,

        @JsonProperty("failed_at")
        Instant failedAt,

        @JsonProperty("cancelled_at")
        Instant cancelledAt,

        @JsonProperty("refunded_at")
        Instant refundedAt,

        @JsonProperty("failure_code")
        String failureCode,

        @JsonProperty("failure_message")
        String failureMessage,

        @JsonProperty("transactions")
        List<PaymentTransactionResponse> transactions,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
