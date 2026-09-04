package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

public record AdminProductVariantRequest(
        @JsonProperty("sku_id")
        Long skuId,

        @JsonProperty("option_name")
        @Size(max = 100)
        String optionName,

        @JsonProperty("option_value")
        @Size(max = 100)
        String optionValue,

        @JsonProperty("unified_size")
        @Size(max = 100)
        String unifiedSize,

        @JsonProperty("inventory_count")
        @Min(0)
        Integer inventoryCount,

        @JsonProperty("available")
        Boolean available,

        @JsonProperty("active")
        Boolean active
) {
}
