package com.example.serviceapiecommerce.dto.admin;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AdminProductImageUploadResponse(
        @JsonProperty("url")
        String url
) {
}
