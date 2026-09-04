package com.example.serviceapiecommerce.dto.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record CheckoutPreviewResponse(
        @JsonProperty("subtotal_amount")
        BigDecimal subtotalAmount,

        @JsonProperty("promotion_discount_amount")
        BigDecimal promotionDiscountAmount,

        @JsonProperty("coupon_discount_amount")
        BigDecimal couponDiscountAmount,

        @JsonProperty("total_discount_amount")
        BigDecimal totalDiscountAmount,

        @JsonProperty("shipping_fee")
        BigDecimal shippingFee,

        @JsonProperty("tax_amount")
        BigDecimal taxAmount,

        @JsonProperty("total_amount")
        BigDecimal totalAmount
) {
}
