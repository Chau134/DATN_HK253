package com.example.serviceapiecommerce.dto.response;

import com.example.serviceapiecommerce.dto.ai.AiSearchFilterDto;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionBoxDto;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiProductSearchResponse(
        @JsonProperty("rewritten_query")
        String rewrittenQuery,

        @JsonProperty("filters")
        AiSearchFilterDto filters,

        @JsonProperty("route")
        String route,

        @JsonProperty("products")
        List<ProductCardResponse> products,

        @JsonProperty("detections")
        List<AiImageDetectionBoxDto> detections,

        @JsonProperty("warnings")
        List<String> warnings
) {
    public AiProductSearchResponse {
        products = products == null ? List.of() : List.copyOf(products);
        detections = detections == null ? List.of() : List.copyOf(detections);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }
}
