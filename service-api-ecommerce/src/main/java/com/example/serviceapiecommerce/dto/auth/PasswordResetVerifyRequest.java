package com.example.serviceapiecommerce.dto.auth;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record PasswordResetVerifyRequest(
        @JsonProperty("email")
        @Email
        @NotBlank
        @Size(max = 320)
        String email,

        @JsonProperty("otp")
        @NotBlank
        @Pattern(regexp = "\\d{6}")
        String otp
) {
}
