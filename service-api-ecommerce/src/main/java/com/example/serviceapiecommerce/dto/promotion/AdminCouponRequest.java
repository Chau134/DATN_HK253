package com.example.serviceapiecommerce.dto.promotion;

import com.example.serviceapiecommerce.entity.CouponStatus;
import com.example.serviceapiecommerce.entity.DiscountType;
import com.example.serviceapiecommerce.entity.PromotionCustomerScope;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.Instant;

public record AdminCouponRequest(
        @JsonProperty("code")
        @NotBlank
        @Size(max = 50)
        String code,

        @JsonProperty("name")
        @NotBlank
        @Size(max = 150)
        String name,

        @JsonProperty("description")
        @Size(max = 2000)
        String description,

        @JsonProperty("discount_type")
        @NotNull
        DiscountType discountType,

        @JsonProperty("discount_value")
        @NotNull
        @DecimalMin("0.00")
        BigDecimal discountValue,

        @JsonProperty("max_discount_amount")
        @DecimalMin("0.00")
        BigDecimal maxDiscountAmount,

        @JsonProperty("min_order_amount")
        @DecimalMin("0.00")
        BigDecimal minOrderAmount,

        @JsonProperty("currency")
        @Size(min = 3, max = 3)
        String currency,

        @JsonProperty("usage_limit")
        @Positive
        Integer usageLimit,

        @JsonProperty("usage_limit_per_user")
        @Positive
        Integer usageLimitPerUser,

        @JsonProperty("status")
        CouponStatus status,

        @JsonProperty("customer_scope")
        PromotionCustomerScope customerScope,

        @JsonProperty("eligible_user_account_id")
        Long eligibleUserAccountId,

        @JsonProperty("customer_segment")
        @Size(max = 100)
        String customerSegment,

        @JsonProperty("starts_at")
        Instant startsAt,

        @JsonProperty("ends_at")
        Instant endsAt
) {
}
