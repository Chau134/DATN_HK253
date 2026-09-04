package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;

public record AiProductIndexItemDto(
        @JsonProperty("product_id")
        String productId,

        @JsonProperty("product_display_name")
        String productDisplayName,

        @JsonProperty("product_display_name_vi")
        String productDisplayNameVi,

        @JsonProperty("brand_name")
        String brandName,

        @JsonProperty("base_colour")
        String baseColour,

        @JsonProperty("base_colour_vi")
        String baseColourVi,

        @JsonProperty("material")
        String material,

        @JsonProperty("material_vi")
        String materialVi,

        @JsonProperty("fit")
        String fit,

        @JsonProperty("fit_vi")
        String fitVi,

        @JsonProperty("season")
        String season,

        @JsonProperty("season_vi")
        String seasonVi,

        @JsonProperty("product_usage")
        String productUsage,

        @JsonProperty("product_usage_vi")
        String productUsageVi,

        @JsonProperty("gender")
        String gender,

        @JsonProperty("gender_vi")
        String genderVi,

        @JsonProperty("description")
        String description,

        @JsonProperty("description_vi")
        String descriptionVi,

        @JsonProperty("categories")
        List<AiCategoryDto> categories,

        @JsonProperty("option_value")
        List<String> optionValue,

        @JsonProperty("unified_size")
        List<String> unifiedSize,

        @JsonProperty("inventory_count")
        Integer inventoryCount,

        @JsonProperty("available")
        Boolean available,

        @JsonProperty("active")
        Boolean active,

        @JsonProperty("selling_price")
        BigDecimal sellingPrice,

        @JsonProperty("vat")
        BigDecimal vat,

        @JsonProperty("image_urls")
        List<String> imageUrls,

        @JsonProperty("attributes")
        Map<String, String> attributes,

        @JsonProperty("attributes_vi")
        Map<String, String> attributesVi,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
}
