package com.example.serviceapiecommerce.dto.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;

public record CatalogProductImageResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("image_type")
        String imageType,

        @JsonProperty("image_url")
        String imageUrl,

        @JsonProperty("sort_order")
        Integer sortOrder
) {
}
