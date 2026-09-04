package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiIndexFailureDto(
        @JsonProperty("product_id")
        String productId,

        @JsonProperty("stage")
        String stage,

        @JsonProperty("reason")
        String reason,

        @JsonProperty("image_url")
        String imageUrl
) {
}
