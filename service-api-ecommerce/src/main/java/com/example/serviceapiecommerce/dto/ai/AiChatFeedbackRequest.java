package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record AiChatFeedbackRequest(
        @JsonProperty("chat_message_id")
        @NotNull
        Long chatMessageId,

        @JsonProperty("user_id")
        @Size(max = 120)
        String userId,

        @JsonProperty("rating")
        @Min(1)
        @Max(5)
        Integer rating,

        @JsonProperty("helpful")
        Boolean helpful,

        @JsonProperty("feedback_type")
        @Size(max = 50)
        String feedbackType,

        @JsonProperty("comment")
        @Size(max = 4000)
        String comment
) {
}
