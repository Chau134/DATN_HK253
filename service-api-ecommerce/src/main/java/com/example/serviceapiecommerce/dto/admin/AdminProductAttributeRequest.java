package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record AdminProductAttributeRequest(
        @JsonProperty("attr_key")
        @NotBlank
        @Size(max = 255)
        String attrKey,

        @JsonProperty("attr_value")
        @Size(max = 5000)
        String attrValue,

        @JsonProperty("attr_value_vi")
        @Size(max = 5000)
        String attrValueVi
) {
}
