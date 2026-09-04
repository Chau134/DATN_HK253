package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiChatResponse(
        @JsonProperty("session_id")
        String sessionId,

        @JsonProperty("message")
        String message,

        @JsonProperty("product_ids")
        List<AiProductResultDto> productIds,

        @JsonProperty("filters")
        AiSearchFilterDto filters,

        @JsonProperty("rewritten_query")
        String rewrittenQuery,

        @JsonProperty("warnings")
        List<String> warnings
) {
    public AiChatResponse {
        productIds = productIds == null ? List.of() : List.copyOf(productIds);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }

    public static AiChatResponse unavailable(AiChatRequest request, String warning) {
        return new AiChatResponse(
                request == null ? null : request.sessionId(),
                "Sorry, the assistant is temporarily unavailable. Please try again in a moment.",
                List.of(),
                null,
                null,
                List.of(warning)
        );
    }
}
