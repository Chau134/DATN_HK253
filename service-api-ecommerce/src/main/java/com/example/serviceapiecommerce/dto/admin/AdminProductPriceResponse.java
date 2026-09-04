package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;

public record AdminProductPriceResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("product_id")
        Long productId,

        @JsonProperty("selling_price")
        BigDecimal sellingPrice,

        @JsonProperty("import_price")
        BigDecimal importPrice,

        @JsonProperty("vat")
        BigDecimal vat,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
