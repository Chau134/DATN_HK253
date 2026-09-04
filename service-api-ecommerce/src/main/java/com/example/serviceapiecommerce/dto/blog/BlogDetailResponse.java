package com.example.serviceapiecommerce.dto.blog;

import com.example.serviceapiecommerce.entity.BlogCategory;
import com.example.serviceapiecommerce.entity.BlogStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record BlogDetailResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("title")
        String title,

        @JsonProperty("slug")
        String slug,

        @JsonProperty("summary")
        String summary,

        @JsonProperty("content")
        String content,

        @JsonProperty("thumbnail_url")
        String thumbnailUrl,

        @JsonProperty("category")
        BlogCategory category,

        @JsonProperty("status")
        BlogStatus status,

        @JsonProperty("author_name")
        String authorName,

        @JsonProperty("published_at")
        Instant publishedAt,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt
) {}
