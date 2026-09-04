package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

public record AdminProductPriceRequest(
        @JsonProperty("selling_price")
        @NotNull
        @DecimalMin("0.00")
        BigDecimal sellingPrice,

        @JsonProperty("import_price")
        @DecimalMin("0.00")
        BigDecimal importPrice,

        @JsonProperty("vat")
        @DecimalMin("0.00")
        BigDecimal vat
) {
}
