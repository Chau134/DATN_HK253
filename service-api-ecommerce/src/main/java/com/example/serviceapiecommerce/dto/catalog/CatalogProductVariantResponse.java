package com.example.serviceapiecommerce.dto.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;

public record CatalogProductVariantResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("sku_id")
        Long skuId,

        @JsonProperty("option_name")
        String optionName,

        @JsonProperty("option_value")
        String optionValue,

        @JsonProperty("unified_size")
        String unifiedSize,

        @JsonProperty("inventory_count")
        Integer inventoryCount,

        @JsonProperty("available")
        Boolean available,

        @JsonProperty("active")
        Boolean active
) {
}
