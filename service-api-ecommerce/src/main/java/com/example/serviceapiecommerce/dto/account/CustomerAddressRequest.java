package com.example.serviceapiecommerce.dto.account;

import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CustomerAddressRequest(
        @JsonProperty("address_type")
        CustomerAddressType addressType,

        @JsonProperty("recipient_name")
        @NotBlank
        @Size(max = 150)
        String recipientName,

        @JsonProperty("phone_number")
        @NotBlank
        @Size(max = 30)
        String phoneNumber,

        @JsonProperty("address_line1")
        @NotBlank
        @Size(max = 255)
        String addressLine1,

        @JsonProperty("address_line2")
        @Size(max = 255)
        String addressLine2,

        @JsonProperty("ward")
        @Size(max = 150)
        String ward,

        @JsonProperty("district")
        @Size(max = 150)
        String district,

        @JsonProperty("city")
        @Size(max = 150)
        String city,

        @JsonProperty("province")
        @Size(max = 150)
        String province,

        @JsonProperty("country_code")
        @Size(max = 2)
        String countryCode,

        @JsonProperty("postal_code")
        @Size(max = 20)
        String postalCode,

        @JsonProperty("is_default")
        Boolean defaultAddress
) {
}
