package com.example.serviceapiecommerce.dto.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record CheckoutRequest(
        @JsonProperty("cart_id")
        Long cartId,

        @JsonProperty("shipping_address_id")
        @NotNull
        Long shippingAddressId,

        @JsonProperty("billing_address_id")
        Long billingAddressId,

        @JsonProperty("coupon_code")
        @Size(max = 50)
        String couponCode,

        @JsonProperty("customer_note")
        @Size(max = 2000)
        String customerNote
) {
}
