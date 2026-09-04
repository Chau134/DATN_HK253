package com.example.serviceapiecommerce.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;
import java.util.List;

public record ProductCardResponse(
        @JsonProperty("product_id")
        String productId,

        @JsonProperty("external_id")
        Long externalId,

        @JsonProperty("title")
        String title,

        @JsonProperty("title_vi")
        String titleVi,

        @JsonProperty("brand")
        String brand,

        @JsonProperty("price")
        BigDecimal price,

        @JsonProperty("discounted_price")
        BigDecimal discountedPrice,

        @JsonProperty("effective_price")
        BigDecimal effectivePrice,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("total_stock")
        Integer totalStock,

        @JsonProperty("available")
        Boolean available,

        @JsonProperty("image_url")
        String imageUrl,

        @JsonProperty("image_urls")
        List<String> imageUrls,

        @JsonProperty("ai_score")
        Double aiScore,

        @JsonProperty("ai_source")
        String aiSource
) {
    public ProductCardResponse {
        imageUrls = imageUrls == null ? List.of() : List.copyOf(imageUrls);
    }
}
