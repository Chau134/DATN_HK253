package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiImageDetectionBoxDto(
        @JsonProperty("bbox")
        AiImageBoundingBoxDto bbox,

        @JsonProperty("confidence")
        Double confidence,

        @JsonProperty("class_id")
        Integer classId,

        @JsonProperty("is_fallback")
        Boolean isFallback
) {
}
