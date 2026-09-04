package com.example.serviceapiecommerce.dto.response;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiChatFeedbackResponse(
        @JsonProperty("feedback_id")
        Long feedbackId,

        @JsonProperty("chat_message_id")
        Long chatMessageId,

        @JsonProperty("rating")
        Integer rating,

        @JsonProperty("helpful")
        Boolean helpful,

        @JsonProperty("feedback_type")
        String feedbackType,

        @JsonProperty("comment")
        String comment
) {
}
