package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import java.util.Map;

public record AiImageDetectionRequest(
        @JsonProperty("image")
        @NotNull
        Map<String, Object> image
) {
}
