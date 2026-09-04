package com.example.serviceapiecommerce.dto.account;

import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.fasterxml.jackson.annotation.JsonProperty;

public record CustomerAddressResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("address_type")
        CustomerAddressType addressType,

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
        String postalCode,

        @JsonProperty("is_default")
        Boolean defaultAddress
) {
    public static CustomerAddressResponse from(CustomerAddress address) {
        return new CustomerAddressResponse(
                address.getId(),
                address.getAddressType(),
                address.getRecipientName(),
                address.getPhoneNumber(),
                address.getAddressLine1(),
                address.getAddressLine2(),
                address.getWard(),
                address.getDistrict(),
                address.getCity(),
                address.getProvince(),
                address.getCountryCode(),
                address.getPostalCode(),
                address.getDefaultAddress()
        );
    }
}
