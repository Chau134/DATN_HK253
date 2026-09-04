package com.example.serviceapiecommerce.dto.error;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ApiFieldError(
        @JsonProperty("field")
        String field,

        @JsonProperty("message")
        String message
) {
}
