package com.example.serviceapiecommerce.dto.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record CatalogProductPriceResponse(
        @JsonProperty("price")
        BigDecimal price,

        @JsonProperty("discounted_price")
        BigDecimal discountedPrice,

        @JsonProperty("effective_price")
        BigDecimal effectivePrice,

        @JsonProperty("vat")
        BigDecimal vat,

        @JsonProperty("currency")
        String currency
) {
}
