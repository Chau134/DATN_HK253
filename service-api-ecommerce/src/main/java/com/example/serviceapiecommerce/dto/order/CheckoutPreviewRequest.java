package com.example.serviceapiecommerce.dto.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Size;

public record CheckoutPreviewRequest(
        @JsonProperty("cart_id")
        Long cartId,

        @JsonProperty("coupon_code")
        @Size(max = 50)
        String couponCode
) {
}
