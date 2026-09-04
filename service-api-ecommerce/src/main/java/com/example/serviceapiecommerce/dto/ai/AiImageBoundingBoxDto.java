package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Min;

public record AiImageBoundingBoxDto(
        @JsonProperty("left")
        @Min(0)
        Integer left,

        @JsonProperty("top")
        @Min(0)
        Integer top,

        @JsonProperty("right")
        @Min(0)
        Integer right,

        @JsonProperty("bottom")
        @Min(0)
        Integer bottom
) {
}
