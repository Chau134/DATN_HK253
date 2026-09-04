package com.example.serviceapiecommerce.dto.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

public record CatalogProductDetailResponse(
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

        @JsonProperty("description")
        String description,

        @JsonProperty("description_vi")
        String descriptionVi,

        @JsonProperty("price")
        CatalogProductPriceResponse price,

        @JsonProperty("image_url")
        String imageUrl,

        @JsonProperty("image_urls")
        List<String> imageUrls,

        @JsonProperty("images")
        List<CatalogProductImageResponse> images,

        @JsonProperty("variants")
        List<CatalogProductVariantResponse> variants,

        @JsonProperty("categories")
        List<CatalogCategoryResponse> categories,

        @JsonProperty("review_summary")
        CatalogProductReviewSummaryResponse reviewSummary,

        @JsonProperty("total_stock")
        Integer totalStock,

        @JsonProperty("available")
        Boolean available,

        @JsonProperty("catalog_add_date")
        Instant catalogAddDate,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {
    public CatalogProductDetailResponse {
        imageUrls = imageUrls == null ? List.of() : List.copyOf(imageUrls);
        images = images == null ? List.of() : List.copyOf(images);
        variants = variants == null ? List.of() : List.copyOf(variants);
        categories = categories == null ? List.of() : List.copyOf(categories);
    }
}
