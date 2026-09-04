package com.example.serviceapiecommerce.dto.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;

public record CatalogCategoryResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("source_category_id")
        Long sourceCategoryId,

        @JsonProperty("level")
        String level,

        @JsonProperty("name")
        String name,

        @JsonProperty("name_vi")
        String nameVi,

        @JsonProperty("canonical_code")
        String canonicalCode,

        @JsonProperty("parent_id")
        Long parentId
) {
}
