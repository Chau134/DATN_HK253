package com.example.serviceapiecommerce.dto.review;

import com.example.serviceapiecommerce.entity.ProductReviewStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record ProductReviewModerationRequest(
        @JsonProperty("status")
        @NotNull
        ProductReviewStatus status,

        @JsonProperty("moderation_reason")
        @Size(max = 150)
        String moderationReason
) {
}
