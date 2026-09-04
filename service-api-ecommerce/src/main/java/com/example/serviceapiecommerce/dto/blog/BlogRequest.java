package com.example.serviceapiecommerce.dto.blog;

import com.example.serviceapiecommerce.entity.BlogCategory;
import com.example.serviceapiecommerce.entity.BlogStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.time.Instant;

public record BlogRequest(
        @NotBlank(message = "Title is required")
        @Size(max = 255, message = "Title cannot exceed 255 characters")
        @JsonProperty("title")
        String title,

        @JsonProperty("summary")
        String summary,

        @JsonProperty("content")
        String content,

        @NotNull(message = "Category is required")
        @JsonProperty("category")
        BlogCategory category,

        @NotNull(message = "Status is required")
        @JsonProperty("status")
        BlogStatus status,

        @JsonProperty("published_at")
        Instant publishedAt
) {}
