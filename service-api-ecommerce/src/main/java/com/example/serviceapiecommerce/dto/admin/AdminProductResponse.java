package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

public record AdminProductResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("external_id")
        Long externalId,

        @JsonProperty("article_number")
        String articleNumber,

        @JsonProperty("title")
        String title,

        @JsonProperty("title_vi")
        String titleVi,

        @JsonProperty("variant_name")
        String variantName,

        @JsonProperty("variant_name_vi")
        String variantNameVi,

        @JsonProperty("brand")
        String brand,

        @JsonProperty("age_group")
        String ageGroup,

        @JsonProperty("age_group_vi")
        String ageGroupVi,

        @JsonProperty("gender")
        String gender,

        @JsonProperty("gender_vi")
        String genderVi,

        @JsonProperty("base_colour")
        String baseColour,

        @JsonProperty("base_colour_vi")
        String baseColourVi,

        @JsonProperty("colour1")
        String colour1,

        @JsonProperty("colour1_vi")
        String colour1Vi,

        @JsonProperty("colour2")
        String colour2,

        @JsonProperty("colour2_vi")
        String colour2Vi,

        @JsonProperty("season")
        String season,

        @JsonProperty("season_vi")
        String seasonVi,

        @JsonProperty("year")
        Integer year,

        @JsonProperty("usage")
        String usage,

        @JsonProperty("usage_vi")
        String usageVi,

        @JsonProperty("material")
        String material,

        @JsonProperty("material_vi")
        String materialVi,

        @JsonProperty("fit")
        String fit,

        @JsonProperty("fit_vi")
        String fitVi,

        @JsonProperty("main_image")
        String mainImage,

        @JsonProperty("description")
        String description,

        @JsonProperty("description_vi")
        String descriptionVi,

        @JsonProperty("catalog_add_date")
        Instant catalogAddDate,

        @JsonProperty("category_ids")
        List<Long> categoryIds,

        @JsonProperty("variants")
        List<AdminProductVariantResponse> variants,

        @JsonProperty("prices")
        List<AdminProductPriceResponse> prices,

        @JsonProperty("images")
        List<AdminProductImageResponse> images,

        @JsonProperty("attributes")
        List<AdminProductAttributeResponse> attributes,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
    public AdminProductResponse {
        categoryIds = categoryIds == null ? List.of() : List.copyOf(categoryIds);
        variants = variants == null ? List.of() : List.copyOf(variants);
        prices = prices == null ? List.of() : List.copyOf(prices);
        images = images == null ? List.of() : List.copyOf(images);
        attributes = attributes == null ? List.of() : List.copyOf(attributes);
    }
}
