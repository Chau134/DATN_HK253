package com.example.serviceapiecommerce.dto.promotion;

import com.example.serviceapiecommerce.entity.CouponStatus;
import com.example.serviceapiecommerce.entity.DiscountType;
import com.example.serviceapiecommerce.entity.PromotionCustomerScope;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;

public record CouponResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("code")
        String code,

        @JsonProperty("name")
        String name,

        @JsonProperty("description")
        String description,

        @JsonProperty("discount_type")
        DiscountType discountType,

        @JsonProperty("discount_value")
        BigDecimal discountValue,

        @JsonProperty("max_discount_amount")
        BigDecimal maxDiscountAmount,

        @JsonProperty("min_order_amount")
        BigDecimal minOrderAmount,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("usage_limit")
        Integer usageLimit,

        @JsonProperty("usage_limit_per_user")
        Integer usageLimitPerUser,

        @JsonProperty("used_count")
        Integer usedCount,

        @JsonProperty("status")
        CouponStatus status,

        @JsonProperty("customer_scope")
        PromotionCustomerScope customerScope,

        @JsonProperty("eligible_user_account_id")
        Long eligibleUserAccountId,

        @JsonProperty("customer_segment")
        String customerSegment,

        @JsonProperty("starts_at")
        Instant startsAt,

        @JsonProperty("ends_at")
        Instant endsAt,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
