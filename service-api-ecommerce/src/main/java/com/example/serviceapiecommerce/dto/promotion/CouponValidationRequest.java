package com.example.serviceapiecommerce.dto.promotion;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;

public record CouponValidationRequest(
        @JsonProperty("code")
        @NotBlank
        @Size(max = 50)
        String code,

        @JsonProperty("order_amount")
        @NotNull
        @DecimalMin("0.00")
        BigDecimal orderAmount,

        @JsonProperty("shipping_fee")
        @DecimalMin("0.00")
        BigDecimal shippingFee,

        @JsonProperty("currency")
        @Size(min = 3, max = 3)
        String currency
) {
}
