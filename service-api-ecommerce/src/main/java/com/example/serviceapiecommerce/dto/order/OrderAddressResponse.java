package com.example.serviceapiecommerce.dto.order;

import com.example.serviceapiecommerce.entity.OrderAddressType;
import com.fasterxml.jackson.annotation.JsonProperty;

public record OrderAddressResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("address_type")
        OrderAddressType addressType,

        @JsonProperty("source_customer_address_id")
        Long sourceCustomerAddressId,

        @JsonProperty("recipient_name")
        String recipientName,

        @JsonProperty("phone_number")
        String phoneNumber,

        @JsonProperty("address_line1")
        String addressLine1,

        @JsonProperty("address_line2")
        String addressLine2,

        @JsonProperty("ward")
        String ward,

        @JsonProperty("district")
        String district,

        @JsonProperty("city")
        String city,

        @JsonProperty("province")
        String province,

        @JsonProperty("country_code")
        String countryCode,

        @JsonProperty("postal_code")
        String postalCode
) {
}
