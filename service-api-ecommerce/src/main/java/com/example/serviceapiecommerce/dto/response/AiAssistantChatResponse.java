package com.example.serviceapiecommerce.dto.response;

import com.example.serviceapiecommerce.dto.ai.AiSearchFilterDto;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiAssistantChatResponse(
        @JsonProperty("session_id")
        String sessionId,

        @JsonProperty("chat_message_id")
        Long chatMessageId,

        @JsonProperty("message")
        String message,

        @JsonProperty("products")
        List<ProductCardResponse> products,

        @JsonProperty("filters")
        AiSearchFilterDto filters,

        @JsonProperty("rewritten_query")
        String rewrittenQuery,

        @JsonProperty("warnings")
        List<String> warnings
) {
    public AiAssistantChatResponse {
        products = products == null ? List.of() : List.copyOf(products);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }
}
