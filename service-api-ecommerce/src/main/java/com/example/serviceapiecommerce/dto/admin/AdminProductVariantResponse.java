package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record AdminProductVariantResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("product_id")
        Long productId,

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
        Boolean active,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
