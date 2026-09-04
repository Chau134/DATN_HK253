package com.example.serviceapiecommerce.dto.error;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

@JsonInclude(JsonInclude.Include.NON_EMPTY)
public record ApiErrorResponse(
        @JsonProperty("error")
        String error,

        @JsonProperty("message")
        String message,

        @JsonProperty("status")
        int status,

        @JsonProperty("path")
        String path,

        @JsonProperty("timestamp")
        String timestamp,

        @JsonProperty("field_errors")
        List<ApiFieldError> fieldErrors
) {
    public ApiErrorResponse {
        fieldErrors = fieldErrors == null ? List.of() : List.copyOf(fieldErrors);
    }

    public static ApiErrorResponse of(String error, String message, int status, String path) {
        return new ApiErrorResponse(error, message, status, path, Instant.now(), List.of());
    }

    public static ApiErrorResponse withFieldErrors(
            String error,
            String message,
            int status,
            String path,
            List<ApiFieldError> fieldErrors
    ) {
        return new ApiErrorResponse(error, message, status, path, Instant.now(), fieldErrors);
    }

    private ApiErrorResponse(
            String error,
            String message,
            int status,
            String path,
            Instant timestamp,
            List<ApiFieldError> fieldErrors
    ) {
        this(error, message, status, path, timestamp.toString(), fieldErrors);
    }
}
