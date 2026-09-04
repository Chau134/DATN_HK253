package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

public record AiTextSearchRequest(
        @JsonProperty("query")
        @Size(max = 1000)
        String query,

        @JsonProperty("filters")
        @Valid
        AiSearchFilterDto filters,

        @JsonProperty("top_k")
        @Min(1)
        @Max(100)
        Integer topK
) {
}
