package com.example.serviceapiecommerce.config;

import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserAccountStatus;
import com.example.serviceapiecommerce.entity.UserRole;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.repository.UserRoleRepository;
import java.time.Instant;
import java.util.Locale;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.support.TransactionTemplate;

@Configuration
public class AdminBootstrapConfig {
    private static final Logger log = LoggerFactory.getLogger(AdminBootstrapConfig.class);
    private static final String ROLE_ADMIN = "ADMIN";

    @Bean
    ApplicationRunner adminBootstrapRunner(
            @Value("${BOOTSTRAP_ADMIN_ENABLED:false}") boolean enabled,
            @Value("${BOOTSTRAP_ADMIN_EMAIL:}") String email,
            @Value("${BOOTSTRAP_ADMIN_PASSWORD:}") String password,
            @Value("${BOOTSTRAP_ADMIN_FULL_NAME:System Admin}") String fullName,
            UserAccountRepository userAccountRepository,
            UserRoleRepository userRoleRepository,
            PasswordEncoder passwordEncoder,
            TransactionTemplate transactionTemplate
    ) {
        return args -> {
            if (!enabled) {
                return;
            }

            String normalizedEmail = normalizeEmail(email);
            if (normalizedEmail == null || password == null || password.isBlank()) {
                log.warn("admin_bootstrap_skipped reason=missing_email_or_password");
                return;
            }

            transactionTemplate.executeWithoutResult(status -> {
                UserAccount existingAccount = userAccountRepository.findByEmailWithRoles(normalizedEmail).orElse(null);
                if (existingAccount != null) {
                    boolean changed = false;
                    Instant now = Instant.now();
                    UserRole adminRole = adminRole(userRoleRepository, now);

                    if (existingAccount.getRoles().stream().noneMatch(role -> ROLE_ADMIN.equals(role.getName()))) {
                        existingAccount.getRoles().add(adminRole);
                        changed = true;
                    }
                    if (existingAccount.getPasswordHash() == null
                            || !passwordEncoder.matches(password, existingAccount.getPasswordHash())) {
                        existingAccount.setPasswordHash(passwordEncoder.encode(password));
                        changed = true;
                    }
                    if (Boolean.FALSE.equals(existingAccount.getPasswordLoginEnabled())) {
                        existingAccount.setPasswordLoginEnabled(true);
                        changed = true;
                    }
                    if (existingAccount.getStatus() != UserAccountStatus.ACTIVE) {
                        existingAccount.setStatus(UserAccountStatus.ACTIVE);
                        changed = true;
                    }
                    if (blankToNull(existingAccount.getFullName()) == null) {
                        existingAccount.setFullName(blankToNull(fullName));
                        changed = true;
                    }
                    if (blankToNull(existingAccount.getDisplayName()) == null) {
                        existingAccount.setDisplayName(blankToNull(fullName));
                        changed = true;
                    }

                    if (changed) {
                        existingAccount.setUpdatedAt(now);
                        userAccountRepository.save(existingAccount);
                        log.info("admin_bootstrap_updated email={}", normalizedEmail);
                    } else {
                        log.info("admin_bootstrap_skipped reason=account_current email={}", normalizedEmail);
                    }
                    return;
                }

                Instant now = Instant.now();
                UserAccount account = new UserAccount();
                account.setEmail(normalizedEmail);
                account.setPasswordHash(passwordEncoder.encode(password));
                account.setPasswordLoginEnabled(true);
                account.setFullName(blankToNull(fullName));
                account.setDisplayName(blankToNull(fullName));
                account.setStatus(UserAccountStatus.ACTIVE);
                account.setEmailVerified(true);
                account.setPhoneVerified(false);
                account.setCreatedAt(now);
                account.setUpdatedAt(now);
                account.getRoles().add(adminRole(userRoleRepository, now));

                userAccountRepository.save(account);
                log.info("admin_bootstrap_created email={}", normalizedEmail);
            });
        };
    }

    private static UserRole adminRole(UserRoleRepository userRoleRepository, Instant now) {
        return userRoleRepository.findByName(ROLE_ADMIN)
                .orElseGet(() -> {
                    UserRole role = new UserRole();
                    role.setName(ROLE_ADMIN);
                    role.setDescription("Administrator role");
                    role.setActive(true);
                    role.setCreatedAt(now);
                    role.setUpdatedAt(now);
                    return userRoleRepository.save(role);
                });
    }

    private static String normalizeEmail(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim().toLowerCase(Locale.ROOT);
    }

    private static String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }
}
