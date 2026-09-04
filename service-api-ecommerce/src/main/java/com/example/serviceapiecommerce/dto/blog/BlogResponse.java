package com.example.serviceapiecommerce.dto.blog;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record BlogResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("title")
        String title,

        @JsonProperty("description")
        String description,

        @JsonProperty("content")
        String content,

        @JsonProperty("img")
        String img,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {}
