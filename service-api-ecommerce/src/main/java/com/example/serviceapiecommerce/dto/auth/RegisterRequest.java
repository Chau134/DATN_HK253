package com.example.serviceapiecommerce.dto.auth;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record RegisterRequest(
        @JsonProperty("email")
        @Email
        @NotBlank
        @Size(max = 320)
        String email,

        @JsonProperty("password")
        @NotBlank
        @Size(min = 8, max = 100)
        String password,

        @JsonProperty("full_name")
        @Size(max = 150)
        String fullName,

        @JsonProperty("display_name")
        @Size(max = 150)
        String displayName,

        @JsonProperty("phone_number")
        @Size(max = 30)
        String phoneNumber
) {
}
