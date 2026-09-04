package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.security.JwtClaims;
import java.time.Instant;

public interface JwtService {
    String createAccessToken(UserAccount account);

    JwtClaims parseAccessToken(String token);

    String createRefreshToken();

    String hashToken(String token);

    Instant refreshTokenExpiresAt();

    long accessTokenTtlSeconds();
}
