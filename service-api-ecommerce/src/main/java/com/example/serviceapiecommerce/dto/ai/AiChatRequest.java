package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.util.Map;

public record AiChatRequest(
        @JsonProperty("session_id")
        @Size(max = 120)
        String sessionId,

        @JsonProperty("user_id")
        @Size(max = 120)
        String userId,

        @JsonProperty("request_id")
        @Size(max = 128)
        String requestId,

        @JsonProperty("turn_sequence")
        @Positive
        Integer turnSequence,

        @JsonProperty("message")
        @Size(max = 4000)
        String message,

        @JsonProperty("image")
        Map<String, Object> image,

        @JsonProperty("crop_box")
        @Valid
        AiImageBoundingBoxDto cropBox,

        @JsonProperty("locale")
        @Size(max = 20)
        String locale
) {
    public AiChatRequest(
            String sessionId,
            String userId,
            String message,
            Map<String, Object> image,
            AiImageBoundingBoxDto cropBox,
            String locale
    ) {
        this(sessionId, userId, null, null, message, image, cropBox, locale);
    }

    public AiChatRequest {
        locale = locale == null || locale.isBlank() ? "vi-VN" : locale;
    }
}
