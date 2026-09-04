package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.util.List;

public record AiSearchFilterDto(
        @JsonProperty("category")
        @Size(max = 150)
        String category,

        @JsonProperty("brand")
        @Size(max = 150)
        String brand,

        @JsonProperty("colors")
        List<String> colors,

        @JsonProperty("sizes")
        List<String> sizes,

        @JsonProperty("min_price")
        @DecimalMin("0.00")
        BigDecimal minPrice,

        @JsonProperty("max_price")
        @DecimalMin("0.00")
        BigDecimal maxPrice,

        @JsonProperty("gender")
        @Size(max = 50)
        String gender,

        @JsonProperty("material")
        @Size(max = 150)
        String material
) {
}
