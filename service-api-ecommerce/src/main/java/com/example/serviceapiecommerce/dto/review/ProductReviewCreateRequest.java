package com.example.serviceapiecommerce.dto.review;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record ProductReviewCreateRequest(
        @JsonProperty("order_item_id")
        @NotNull
        Long orderItemId,

        @JsonProperty("rating")
        @NotNull
        @Min(1)
        @Max(5)
        Integer rating,

        @JsonProperty("title")
        @Size(max = 150)
        String title,

        @JsonProperty("content")
        @Size(max = 5000)
        String content
) {
}
