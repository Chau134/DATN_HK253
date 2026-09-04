package com.example.serviceapiecommerce.dto.auth;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record LoginRequest(
        @JsonProperty("email")
        @Email
        @NotBlank
        @Size(max = 320)
        String email,

        @JsonProperty("password")
        @NotBlank
        @Size(max = 100)
        String password
) {
}
