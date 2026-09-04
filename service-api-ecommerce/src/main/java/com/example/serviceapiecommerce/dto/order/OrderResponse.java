package com.example.serviceapiecommerce.dto.order;

import com.example.serviceapiecommerce.entity.OrderStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record OrderResponse(
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

        @JsonProperty("subtotal_amount")
        BigDecimal subtotalAmount,

        @JsonProperty("discount_amount")
        BigDecimal discountAmount,

        @JsonProperty("shipping_fee")
        BigDecimal shippingFee,

        @JsonProperty("tax_amount")
        BigDecimal taxAmount,

        @JsonProperty("total_amount")
        BigDecimal totalAmount,

        @JsonProperty("latest_payment")
        OrderPaymentSummaryResponse latestPayment,

        @JsonProperty("customer_note")
        String customerNote,

        @JsonProperty("placed_at")
        Instant placedAt,

        @JsonProperty("cancelled_at")
        Instant cancelledAt,

        @JsonProperty("items")
        List<OrderItemResponse> items,

        @JsonProperty("addresses")
        List<OrderAddressResponse> addresses,

        @JsonProperty("status_history")
        List<OrderStatusHistoryResponse> statusHistory,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt,

        @JsonProperty("is_reviewed")
        Boolean isReviewed
) {
}
