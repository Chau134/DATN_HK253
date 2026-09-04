package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AdminCategoryResponse(
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

        @JsonProperty("active")
        Boolean active,

        @JsonProperty("parent_id")
        Long parentId
) {
}
