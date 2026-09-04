package com.example.serviceapiecommerce.dto.auth;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record PasswordResetConfirmRequest(
        @JsonProperty("reset_token")
        @NotBlank
        String resetToken,

        @JsonProperty("new_password")
        @NotBlank
        @Size(min = 8, max = 100)
        String newPassword,

        @JsonProperty("confirm_password")
        @NotBlank
        @Size(min = 8, max = 100)
        String confirmPassword
) {
}
