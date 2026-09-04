package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.security.JwtClaims;
import com.example.serviceapiecommerce.service.JwtService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class JwtServiceImpl implements JwtService {
    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String TOKEN_TYPE_ACCESS = "access";
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final ObjectMapper objectMapper;
    private final byte[] secretBytes;
    private final long accessTokenTtlSeconds;
    private final long refreshTokenTtlDays;
    private final SecureRandom secureRandom = new SecureRandom();

    public JwtServiceImpl(
            @Value("${app.security.jwt.secret}") String secret,
            @Value("${app.security.jwt.access-token-ttl-seconds}") long accessTokenTtlSeconds,
            @Value("${app.security.jwt.refresh-token-ttl-days}") long refreshTokenTtlDays
    ) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalArgumentException("JWT secret must not be blank");
        }
        this.objectMapper = new ObjectMapper();
        this.secretBytes = secret.getBytes(StandardCharsets.UTF_8);
        this.accessTokenTtlSeconds = accessTokenTtlSeconds;
        this.refreshTokenTtlDays = refreshTokenTtlDays;
    }

    @Override
    public String createAccessToken(UserAccount account) {
        Instant issuedAt = Instant.now();
        Instant expiresAt = issuedAt.plusSeconds(accessTokenTtlSeconds);
        List<String> roles = account.getRoles().stream()
                .filter(role -> role.getActive() == null || role.getActive())
                .map(role -> role.getName())
                .sorted()
                .toList();

        Map<String, Object> header = Map.of("alg", "HS256", "typ", "JWT");
        Map<String, Object> payload = Map.of(
                "sub", account.getId(),
                "email", account.getEmail(),
                "roles", roles,
                "type", TOKEN_TYPE_ACCESS,
                "iat", issuedAt.getEpochSecond(),
                "exp", expiresAt.getEpochSecond()
        );
        String unsigned = base64Url(json(header)) + "." + base64Url(json(payload));
        return unsigned + "." + base64Url(sign(unsigned));
    }

    @Override
    public JwtClaims parseAccessToken(String token) {
        String[] parts = token == null ? new String[0] : token.split("\\.");
        if (parts.length != 3) {
            throw new IllegalArgumentException("invalid_jwt");
        }
        String unsigned = parts[0] + "." + parts[1];
        byte[] expectedSignature = sign(unsigned);
        byte[] actualSignature = base64UrlDecode(parts[2]);
        if (!MessageDigest.isEqual(expectedSignature, actualSignature)) {
            throw new IllegalArgumentException("invalid_jwt_signature");
        }

        Map<String, Object> payload = readMap(base64UrlDecode(parts[1]));
        String type = stringValue(payload.get("type"));
        if (!TOKEN_TYPE_ACCESS.equals(type)) {
            throw new IllegalArgumentException("invalid_jwt_type");
        }
        Instant expiresAt = Instant.ofEpochSecond(longValue(payload.get("exp")));
        if (!expiresAt.isAfter(Instant.now())) {
            throw new IllegalArgumentException("expired_jwt");
        }

        return new JwtClaims(
                longValue(payload.get("sub")),
                stringValue(payload.get("email")),
                stringList(payload.get("roles")),
                type,
                Instant.ofEpochSecond(longValue(payload.get("iat"))),
                expiresAt
        );
    }

    @Override
    public String createRefreshToken() {
        byte[] bytes = new byte[48];
        secureRandom.nextBytes(bytes);
        return base64Url(bytes);
    }

    @Override
    public String hashToken(String token) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return base64Url(digest.digest(token.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception exception) {
            throw new IllegalStateException("Could not hash token", exception);
        }
    }

    @Override
    public Instant refreshTokenExpiresAt() {
        return Instant.now().plus(Duration.ofDays(refreshTokenTtlDays));
    }

    @Override
    public long accessTokenTtlSeconds() {
        return accessTokenTtlSeconds;
    }

    private byte[] sign(String unsigned) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(secretBytes, HMAC_ALGORITHM));
            return mac.doFinal(unsigned.getBytes(StandardCharsets.UTF_8));
        } catch (Exception exception) {
            throw new IllegalStateException("Could not sign JWT", exception);
        }
    }

    private byte[] json(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsBytes(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Could not serialize JWT", exception);
        }
    }

    private Map<String, Object> readMap(byte[] value) {
        try {
            return objectMapper.readValue(value, MAP_TYPE);
        } catch (Exception exception) {
            throw new IllegalArgumentException("invalid_jwt_payload", exception);
        }
    }

    private static String base64Url(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private static byte[] base64UrlDecode(String value) {
        return Base64.getUrlDecoder().decode(value);
    }

    private static String stringValue(Object value) {
        return value == null ? null : value.toString();
    }

    private static Long longValue(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        return Long.parseLong(value.toString());
    }

    private static List<String> stringList(Object value) {
        if (!(value instanceof List<?> list)) {
            return List.of();
        }
        return list.stream().map(Object::toString).toList();
    }
}
