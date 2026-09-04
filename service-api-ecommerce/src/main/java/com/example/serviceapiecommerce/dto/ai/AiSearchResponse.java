package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiSearchResponse(
        @JsonProperty("rewritten_query")
        String rewrittenQuery,

        @JsonProperty("filters")
        AiSearchFilterDto filters,

        @JsonProperty("route")
        String route,

        @JsonProperty("product_ids")
        List<String> productIds,

        @JsonProperty("results")
        List<AiProductResultDto> results,

        @JsonProperty("detections")
        List<AiImageDetectionBoxDto> detections,

        @JsonProperty("warnings")
        List<String> warnings
) {
    public AiSearchResponse {
        productIds = productIds == null ? List.of() : List.copyOf(productIds);
        results = results == null ? List.of() : List.copyOf(results);
        detections = detections == null ? List.of() : List.copyOf(detections);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }

    public static AiSearchResponse unavailable(String rewrittenQuery, AiSearchFilterDto filters, String warning) {
        return new AiSearchResponse(
                rewrittenQuery,
                filters,
                null,
                List.of(),
                List.of(),
                List.of(),
                List.of(warning)
        );
    }
}
