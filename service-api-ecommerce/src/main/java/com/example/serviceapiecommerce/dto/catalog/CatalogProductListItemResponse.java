package com.example.serviceapiecommerce.dto.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record CatalogProductListItemResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("external_id")
        Long externalId,

        @JsonProperty("title")
        String title,

        @JsonProperty("title_vi")
        String titleVi,

        @JsonProperty("brand")
        String brand,

        @JsonProperty("gender")
        String gender,

        @JsonProperty("gender_vi")
        String genderVi,

        @JsonProperty("base_colour")
        String baseColour,

        @JsonProperty("base_colour_vi")
        String baseColourVi,

        @JsonProperty("price")
        CatalogProductPriceResponse price,

        @JsonProperty("image_url")
        String imageUrl,

        @JsonProperty("image_urls")
        List<String> imageUrls,

        @JsonProperty("categories")
        List<CatalogCategoryResponse> categories,

        @JsonProperty("review_summary")
        CatalogProductReviewSummaryResponse reviewSummary,

        @JsonProperty("total_stock")
        Integer totalStock,

        @JsonProperty("available")
        Boolean available
) {
    public CatalogProductListItemResponse {
        imageUrls = imageUrls == null ? List.of() : List.copyOf(imageUrls);
        categories = categories == null ? List.of() : List.copyOf(categories);
    }
}
