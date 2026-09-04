package com.example.serviceapiecommerce.dto.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record CatalogProductReviewSummaryResponse(
        @JsonProperty("review_count")
        Integer reviewCount,

        @JsonProperty("approved_review_count")
        Integer approvedReviewCount,

        @JsonProperty("average_rating")
        BigDecimal averageRating,

        @JsonProperty("rating_1_count")
        Integer rating1Count,

        @JsonProperty("rating_2_count")
        Integer rating2Count,

        @JsonProperty("rating_3_count")
        Integer rating3Count,

        @JsonProperty("rating_4_count")
        Integer rating4Count,

        @JsonProperty("rating_5_count")
        Integer rating5Count
) {
}
