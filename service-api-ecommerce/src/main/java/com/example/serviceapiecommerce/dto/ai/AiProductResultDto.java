package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiProductResultDto(
        @JsonProperty("product_id")
        String productId,

        @JsonProperty("score")
        Double score,

        @JsonProperty("source")
        String source
) {
}
