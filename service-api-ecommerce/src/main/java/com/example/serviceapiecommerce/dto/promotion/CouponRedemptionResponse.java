package com.example.serviceapiecommerce.dto.promotion;

import com.example.serviceapiecommerce.entity.CouponRedemptionStatus;
import com.example.serviceapiecommerce.entity.DiscountType;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;

public record CouponRedemptionResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("coupon_id")
        Long couponId,

        @JsonProperty("user_account_id")
        Long userAccountId,

        @JsonProperty("order_id")
        Long orderId,

        @JsonProperty("redemption_key")
        String redemptionKey,

        @JsonProperty("coupon_code")
        String couponCode,

        @JsonProperty("discount_type")
        DiscountType discountType,

        @JsonProperty("discount_value")
        BigDecimal discountValue,

        @JsonProperty("discount_amount")
        BigDecimal discountAmount,

        @JsonProperty("order_amount")
        BigDecimal orderAmount,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("status")
        CouponRedemptionStatus status,

        @JsonProperty("redeemed_at")
        Instant redeemedAt,

        @JsonProperty("cancelled_at")
        Instant cancelledAt,

        @JsonProperty("cancel_reason")
        String cancelReason,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
