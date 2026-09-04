package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record AdminProductImageRequest(
        @JsonProperty("image_type")
        @NotBlank
        @Size(max = 50)
        String imageType,

        @JsonProperty("image_url")
        @NotBlank
        @Size(max = 2000)
        String imageUrl,

        @JsonProperty("sort_order")
        Integer sortOrder
) {
}
