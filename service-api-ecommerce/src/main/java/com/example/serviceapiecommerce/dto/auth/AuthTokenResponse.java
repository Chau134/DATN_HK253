package com.example.serviceapiecommerce.dto.auth;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AuthTokenResponse(
        @JsonProperty("access_token")
        String accessToken,

        @JsonProperty("refresh_token")
        String refreshToken,

        @JsonProperty("token_type")
        String tokenType,

        @JsonProperty("expires_in")
        long expiresIn,

        @JsonProperty("user")
        AuthUserResponse user
) {
    public AuthTokenResponse(String accessToken, String refreshToken, long expiresIn, AuthUserResponse user) {
        this(accessToken, refreshToken, "Bearer", expiresIn, user);
    }
}
