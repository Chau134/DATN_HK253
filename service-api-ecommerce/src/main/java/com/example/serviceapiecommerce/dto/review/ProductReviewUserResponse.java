package com.example.serviceapiecommerce.dto.review;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ProductReviewUserResponse(
        @JsonProperty("display_name")
        String displayName,

        @JsonProperty("full_name")
        String fullName,

        @JsonProperty("email")
        String email,

        @JsonProperty("avatar_url")
        String avatarUrl
) {
}
