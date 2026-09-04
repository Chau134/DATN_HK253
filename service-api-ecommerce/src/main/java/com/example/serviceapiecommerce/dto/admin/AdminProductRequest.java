package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;

public record AdminProductRequest(
        @JsonProperty("id")
        Long id,

        @JsonProperty("external_id")
        Long externalId,

        @JsonProperty("article_number")
        @Size(max = 100)
        String articleNumber,

        @JsonProperty("title")
        @NotBlank
        @Size(max = 255)
        String title,

        @JsonProperty("title_vi")
        @Size(max = 255)
        String titleVi,

        @JsonProperty("variant_name")
        @Size(max = 255)
        String variantName,

        @JsonProperty("variant_name_vi")
        @Size(max = 255)
        String variantNameVi,

        @JsonProperty("brand")
        @Size(max = 150)
        String brand,

        @JsonProperty("age_group")
        @Size(max = 100)
        String ageGroup,

        @JsonProperty("age_group_vi")
        @Size(max = 100)
        String ageGroupVi,

        @JsonProperty("gender")
        @Size(max = 50)
        String gender,

        @JsonProperty("gender_vi")
        @Size(max = 50)
        String genderVi,

        @JsonProperty("base_colour")
        @Size(max = 100)
        String baseColour,

        @JsonProperty("base_colour_vi")
        @Size(max = 100)
        String baseColourVi,

        @JsonProperty("colour1")
        @Size(max = 100)
        String colour1,

        @JsonProperty("colour1_vi")
        @Size(max = 100)
        String colour1Vi,

        @JsonProperty("colour2")
        @Size(max = 100)
        String colour2,

        @JsonProperty("colour2_vi")
        @Size(max = 100)
        String colour2Vi,

        @JsonProperty("season")
        @Size(max = 50)
        String season,

        @JsonProperty("season_vi")
        @Size(max = 50)
        String seasonVi,

        @JsonProperty("year")
        Integer year,

        @JsonProperty("usage")
        @Size(max = 100)
        String usage,

        @JsonProperty("usage_vi")
        @Size(max = 100)
        String usageVi,

        @JsonProperty("material")
        @Size(max = 150)
        String material,

        @JsonProperty("material_vi")
        @Size(max = 150)
        String materialVi,

        @JsonProperty("fit")
        @Size(max = 150)
        String fit,

        @JsonProperty("fit_vi")
        @Size(max = 150)
        String fitVi,

        @JsonProperty("main_image")
        @Size(max = 2000)
        String mainImage,

        @JsonProperty("description")
        @Size(max = 5000)
        String description,

        @JsonProperty("description_vi")
        @Size(max = 5000)
        String descriptionVi,

        @JsonProperty("catalog_add_date")
        Instant catalogAddDate,

        @JsonProperty("category_ids")
        List<Long> categoryIds
) {
    public AdminProductRequest {
        categoryIds = categoryIds == null ? List.of() : List.copyOf(categoryIds);
    }
}
