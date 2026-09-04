package com.example.serviceapiecommerce.security;

import java.time.Instant;
import java.util.List;

public record JwtClaims(
        Long userId,
        String email,
        List<String> roles,
        String type,
        Instant issuedAt,
        Instant expiresAt
) {
}
