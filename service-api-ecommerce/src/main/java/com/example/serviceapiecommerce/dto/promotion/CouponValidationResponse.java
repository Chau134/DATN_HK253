package com.example.serviceapiecommerce.dto.promotion;

import com.example.serviceapiecommerce.entity.DiscountType;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record CouponValidationResponse(
        @JsonProperty("coupon_id")
        Long couponId,

        @JsonProperty("code")
        String code,

        @JsonProperty("discount_type")
        DiscountType discountType,

        @JsonProperty("discount_value")
        BigDecimal discountValue,

        @JsonProperty("discount_amount")
        BigDecimal discountAmount,

        @JsonProperty("order_amount")
        BigDecimal orderAmount,

        @JsonProperty("shipping_fee")
        BigDecimal shippingFee,

        @JsonProperty("total_after_discount")
        BigDecimal totalAfterDiscount,

        @JsonProperty("currency")
        String currency
) {
}
