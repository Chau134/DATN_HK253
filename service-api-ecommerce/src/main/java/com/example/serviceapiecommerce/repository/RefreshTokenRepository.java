package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.RefreshToken;
import com.example.serviceapiecommerce.entity.RefreshTokenStatus;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RefreshTokenRepository extends JpaRepository<RefreshToken, Long> {
    Optional<RefreshToken> findByTokenHash(String tokenHash);

    boolean existsByTokenHash(String tokenHash);

    List<RefreshToken> findByUserAccount_IdAndStatusOrderByExpiresAtDesc(
            Long userAccountId,
            RefreshTokenStatus status
    );

    long deleteByExpiresAtBefore(Instant expiresAt);
}
