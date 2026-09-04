package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record AdminProductAttributeResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("product_id")
        Long productId,

        @JsonProperty("attr_key")
        String attrKey,

        @JsonProperty("attr_value")
        String attrValue,

        @JsonProperty("attr_value_vi")
        String attrValueVi,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
