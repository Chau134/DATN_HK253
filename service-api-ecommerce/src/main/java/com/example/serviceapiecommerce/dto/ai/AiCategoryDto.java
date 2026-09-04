package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiCategoryDto(
        @JsonProperty("category_code")
        String categoryCode,

        @JsonProperty("category_level")
        String categoryLevel,

        @JsonProperty("category_name")
        String categoryName,

        @JsonProperty("category_name_vi")
        String categoryNameVi
) {
}
