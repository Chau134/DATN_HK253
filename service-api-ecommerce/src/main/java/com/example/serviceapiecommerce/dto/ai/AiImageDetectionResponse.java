package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiImageDetectionResponse(
        @JsonProperty("image_width")
        Integer imageWidth,

        @JsonProperty("image_height")
        Integer imageHeight,

        @JsonProperty("detections")
        List<AiImageDetectionBoxDto> detections,

        @JsonProperty("warnings")
        List<String> warnings
) {
    public AiImageDetectionResponse {
        detections = detections == null ? List.of() : List.copyOf(detections);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }

    public static AiImageDetectionResponse unavailable(String warning) {
        return new AiImageDetectionResponse(null, null, List.of(), List.of(warning));
    }
}
