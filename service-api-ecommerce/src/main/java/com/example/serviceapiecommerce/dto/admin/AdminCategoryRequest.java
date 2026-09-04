package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record AdminCategoryRequest(
        @JsonProperty("source_category_id")
        Long sourceCategoryId,

        @JsonProperty("level")
        @NotBlank
        @Size(max = 50)
        String level,

        @JsonProperty("name")
        @NotBlank
        @Size(max = 150)
        String name,

        @JsonProperty("name_vi")
        @NotBlank
        @Size(max = 150)
        String nameVi,

        @JsonProperty("parent_id")
        Long parentId,

        @JsonProperty("active")
        Boolean active
) {
}
