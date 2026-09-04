package com.example.serviceapiecommerce.dto.auth;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record PasswordResetVerifyResponse(
        @JsonProperty("reset_token")
        String resetToken,

        @JsonProperty("expires_at")
        Instant expiresAt
) {
}
