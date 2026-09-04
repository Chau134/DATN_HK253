package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import java.util.Map;

public record AiImageSearchRequest(
        @JsonProperty("image")
        @NotNull
        Map<String, Object> image,

        @JsonProperty("crop_box")
        @Valid
        AiImageBoundingBoxDto cropBox,

        @JsonProperty("filters")
        @Valid
        AiSearchFilterDto filters,

        @JsonProperty("top_k")
        @Min(1)
        @Max(100)
        Integer topK
) {
}
