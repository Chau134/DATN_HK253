package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.PasswordResetOtp;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PasswordResetOtpRepository extends JpaRepository<PasswordResetOtp, Long> {
    List<PasswordResetOtp> findByUserAccountIdAndUsedAtIsNull(Long userAccountId);

    Optional<PasswordResetOtp> findTopByEmailIgnoreCaseAndUsedAtIsNullOrderByCreatedAtDesc(String email);

    Optional<PasswordResetOtp> findTopByResetTokenHashAndUsedAtIsNullOrderByCreatedAtDesc(String resetTokenHash);
}
