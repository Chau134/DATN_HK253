package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.auth.AuthTokenResponse;
import com.example.serviceapiecommerce.dto.auth.AuthUserResponse;
import com.example.serviceapiecommerce.dto.auth.ChangePasswordRequest;
import com.example.serviceapiecommerce.dto.auth.LoginRequest;
import com.example.serviceapiecommerce.dto.auth.LogoutRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetConfirmRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetVerifyRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetVerifyResponse;
import com.example.serviceapiecommerce.dto.auth.RefreshTokenRequest;
import com.example.serviceapiecommerce.dto.auth.RegisterRequest;
import com.example.serviceapiecommerce.entity.CustomerProfile;
import com.example.serviceapiecommerce.entity.PasswordResetOtp;
import com.example.serviceapiecommerce.entity.RefreshToken;
import com.example.serviceapiecommerce.entity.RefreshTokenStatus;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserAccountStatus;
import com.example.serviceapiecommerce.entity.UserRole;
import com.example.serviceapiecommerce.repository.CustomerProfileRepository;
import com.example.serviceapiecommerce.repository.PasswordResetOtpRepository;
import com.example.serviceapiecommerce.repository.RefreshTokenRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.repository.UserRoleRepository;
import com.example.serviceapiecommerce.service.AuthService;
import com.example.serviceapiecommerce.service.JwtService;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AuthServiceImpl implements AuthService {
    private static final Logger log = LoggerFactory.getLogger(AuthServiceImpl.class);
    private static final String ROLE_CUSTOMER = "CUSTOMER";
    private static final int RESET_TOKEN_BYTES = 48;

    private final UserAccountRepository userAccountRepository;
    private final UserRoleRepository userRoleRepository;
    private final CustomerProfileRepository customerProfileRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final PasswordResetOtpRepository passwordResetOtpRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final JavaMailSender mailSender;
    private final String mailFrom;
    private final String mailUsername;
    private final long otpTtlMinutes;
    private final long resetTokenTtlMinutes;
    private final int maxOtpAttempts;
    private final SecureRandom secureRandom = new SecureRandom();

    public AuthServiceImpl(
            UserAccountRepository userAccountRepository,
            UserRoleRepository userRoleRepository,
            CustomerProfileRepository customerProfileRepository,
            RefreshTokenRepository refreshTokenRepository,
            PasswordResetOtpRepository passwordResetOtpRepository,
            PasswordEncoder passwordEncoder,
            JwtService jwtService,
            ObjectProvider<JavaMailSender> mailSenderProvider,
            @Value("${app.auth.password-reset.otp-ttl-minutes:10}") long otpTtlMinutes,
            @Value("${app.auth.password-reset.reset-token-ttl-minutes:15}") long resetTokenTtlMinutes,
            @Value("${app.auth.password-reset.max-attempts:5}") int maxOtpAttempts,
            @Value("${app.mail.from:}") String mailFrom,
            @Value("${spring.mail.username:}") String mailUsername
    ) {
        this.userAccountRepository = userAccountRepository;
        this.userRoleRepository = userRoleRepository;
        this.customerProfileRepository = customerProfileRepository;
        this.refreshTokenRepository = refreshTokenRepository;
        this.passwordResetOtpRepository = passwordResetOtpRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
        this.mailSender = mailSenderProvider.getIfAvailable();
        this.otpTtlMinutes = Math.max(1, otpTtlMinutes);
        this.resetTokenTtlMinutes = Math.max(1, resetTokenTtlMinutes);
        this.maxOtpAttempts = Math.max(1, maxOtpAttempts);
        this.mailFrom = blankToNull(mailFrom);
        this.mailUsername = blankToNull(mailUsername);
    }

    @Override
    @Transactional
    public AuthTokenResponse register(RegisterRequest request, String ipAddress, String userAgent) {
        String email = normalizeEmail(request.email());
        if (userAccountRepository.existsByEmailIgnoreCase(email)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "email_already_registered");
        }

        String phoneNumber = blankToNull(request.phoneNumber());
        if (phoneNumber != null && userAccountRepository.existsByPhoneNumber(phoneNumber)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "phone_number_already_registered");
        }

        Instant now = Instant.now();
        UserAccount account = new UserAccount();
        account.setEmail(email);
        account.setPhoneNumber(phoneNumber);
        account.setPasswordHash(passwordEncoder.encode(request.password()));
        account.setPasswordLoginEnabled(true);
        account.setFullName(blankToNull(request.fullName()));
        account.setDisplayName(blankToNull(request.displayName()));
        account.setStatus(UserAccountStatus.ACTIVE);
        account.setEmailVerified(false);
        account.setPhoneVerified(false);
        account.setCreatedAt(now);
        account.setUpdatedAt(now);
        ensureCustomerRole(account);

        UserAccount saved = userAccountRepository.save(account);
        createCustomerProfile(saved, now);
        return issueTokens(saved, ipAddress, userAgent);
    }

    @Override
    @Transactional
    public AuthTokenResponse login(LoginRequest request, String ipAddress, String userAgent) {
        UserAccount account = userAccountRepository.findByEmailWithRoles(normalizeEmail(request.email()))
                .orElseThrow(() -> unauthorized("invalid_credentials"));
        if (account.getStatus() != UserAccountStatus.ACTIVE) {
            throw unauthorized("account_not_active");
        }
        if (Boolean.FALSE.equals(account.getPasswordLoginEnabled())) {
            throw unauthorized("password_login_not_enabled");
        }
        if (!passwordEncoder.matches(request.password(), account.getPasswordHash())) {
            throw unauthorized("invalid_credentials");
        }

        Instant now = Instant.now();
        account.setLastLoginAt(now);
        account.setUpdatedAt(now);
        userAccountRepository.save(account);
        return issueTokens(account, ipAddress, userAgent);
    }

    @Override
    @Transactional
    public AuthTokenResponse loginWithGoogleOAuth(
            String email,
            String fullName,
            String avatarUrl,
            String ipAddress,
            String userAgent
    ) {
        String normalizedEmail = normalizeEmail(email);
        if (normalizedEmail == null || normalizedEmail.isBlank()) {
            throw unauthorized("google_email_required");
        }

        Instant now = Instant.now();
        UserAccount account = userAccountRepository.findByEmailWithRoles(normalizedEmail)
                .map(existing -> updateExistingGoogleAccount(existing, fullName, avatarUrl, now))
                .orElseGet(() -> createGoogleCustomer(normalizedEmail, fullName, avatarUrl, now));

        if (account.getStatus() != UserAccountStatus.ACTIVE) {
            throw unauthorized("account_not_active");
        }

        account.setLastLoginAt(now);
        account.setUpdatedAt(now);
        UserAccount saved = userAccountRepository.save(account);
        return issueTokens(saved, ipAddress, userAgent);
    }

    @Override
    @Transactional
    public AuthTokenResponse refresh(RefreshTokenRequest request, String ipAddress, String userAgent) {
        String oldHash = jwtService.hashToken(request.refreshToken());
        RefreshToken oldToken = refreshTokenRepository.findByTokenHash(oldHash)
                .orElseThrow(() -> unauthorized("invalid_refresh_token"));
        Instant now = Instant.now();
        if (oldToken.getStatus() != RefreshTokenStatus.ACTIVE || !oldToken.getExpiresAt().isAfter(now)) {
            throw unauthorized("invalid_refresh_token");
        }

        UserAccount account = userAccountRepository.findByIdWithRoles(oldToken.getUserAccount().getId())
                .orElseThrow(() -> unauthorized("invalid_refresh_token"));
        if (account.getStatus() != UserAccountStatus.ACTIVE) {
            throw unauthorized("account_not_active");
        }

        String newRefreshToken = jwtService.createRefreshToken();
        String newHash = jwtService.hashToken(newRefreshToken);
        oldToken.setStatus(RefreshTokenStatus.REVOKED);
        oldToken.setRevokedAt(now);
        oldToken.setReplacedByTokenHash(newHash);
        oldToken.setUpdatedAt(now);
        refreshTokenRepository.save(oldToken);

        RefreshToken savedRefreshToken = newRefreshToken(account, newHash, ipAddress, userAgent, now);
        refreshTokenRepository.save(savedRefreshToken);
        return new AuthTokenResponse(
                jwtService.createAccessToken(account),
                newRefreshToken,
                jwtService.accessTokenTtlSeconds(),
                AuthUserResponse.from(account)
        );
    }

    @Override
    @Transactional
    public void logout(LogoutRequest request) {
        String tokenHash = jwtService.hashToken(request.refreshToken());
        RefreshToken token = refreshTokenRepository.findByTokenHash(tokenHash)
                .orElseThrow(() -> unauthorized("invalid_refresh_token"));
        if (token.getStatus() == RefreshTokenStatus.ACTIVE) {
            Instant now = Instant.now();
            token.setStatus(RefreshTokenStatus.REVOKED);
            token.setRevokedAt(now);
            token.setUpdatedAt(now);
            refreshTokenRepository.save(token);
        }
    }

    @Override
    @Transactional
    public void requestPasswordReset(PasswordResetRequest request) {
        String email = normalizeEmail(request.email());
        UserAccount account = userAccountRepository.findByEmailIgnoreCase(email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "email_not_found"));
        if (account.getStatus() != UserAccountStatus.ACTIVE) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "account_not_active");
        }

        Instant now = Instant.now();
        List<PasswordResetOtp> activeOtps = passwordResetOtpRepository
                .findByUserAccountIdAndUsedAtIsNull(account.getId());
        activeOtps.forEach(otp -> {
            otp.setUsedAt(now);
            otp.setUpdatedAt(now);
        });
        passwordResetOtpRepository.saveAll(activeOtps);

        String rawOtp = generateOtp();
        PasswordResetOtp otp = new PasswordResetOtp();
        otp.setUserAccount(account);
        otp.setEmail(email);
        otp.setOtpHash(passwordEncoder.encode(rawOtp));
        otp.setFailedAttempts(0);
        otp.setMaxFailedAttempts(maxOtpAttempts);
        otp.setExpiresAt(now.plus(Duration.ofMinutes(otpTtlMinutes)));
        otp.setCreatedAt(now);
        otp.setUpdatedAt(now);
        passwordResetOtpRepository.save(otp);

        sendPasswordResetEmail(account, rawOtp);
    }

    @Override
    @Transactional
    public PasswordResetVerifyResponse verifyPasswordResetOtp(PasswordResetVerifyRequest request) {
        String email = normalizeEmail(request.email());
        PasswordResetOtp otp = passwordResetOtpRepository
                .findTopByEmailIgnoreCaseAndUsedAtIsNullOrderByCreatedAtDesc(email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_otp"));

        Instant now = Instant.now();
        ensureOtpCanBeChecked(otp, now);
        if (!passwordEncoder.matches(request.otp(), otp.getOtpHash())) {
            int failedAttempts = otp.getFailedAttempts() + 1;
            otp.setFailedAttempts(failedAttempts);
            otp.setUpdatedAt(now);
            passwordResetOtpRepository.save(otp);
            if (failedAttempts >= otp.getMaxFailedAttempts()) {
                throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "otp_attempts_exceeded");
            }
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_otp");
        }

        String resetToken = createResetToken();
        Instant resetTokenExpiresAt = now.plus(Duration.ofMinutes(resetTokenTtlMinutes));
        otp.setResetTokenHash(jwtService.hashToken(resetToken));
        otp.setResetTokenExpiresAt(resetTokenExpiresAt);
        otp.setVerifiedAt(now);
        otp.setUpdatedAt(now);
        passwordResetOtpRepository.save(otp);
        return new PasswordResetVerifyResponse(resetToken, resetTokenExpiresAt);
    }

    @Override
    @Transactional
    public void confirmPasswordReset(PasswordResetConfirmRequest request) {
        if (!request.newPassword().equals(request.confirmPassword())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "password_confirmation_mismatch");
        }

        String resetTokenHash = jwtService.hashToken(request.resetToken());
        PasswordResetOtp otp = passwordResetOtpRepository
                .findTopByResetTokenHashAndUsedAtIsNullOrderByCreatedAtDesc(resetTokenHash)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_reset_token"));
        Instant now = Instant.now();
        if (otp.getVerifiedAt() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_reset_token");
        }
        if (otp.getResetTokenExpiresAt() == null || !otp.getResetTokenExpiresAt().isAfter(now)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "reset_token_expired");
        }

        UserAccount account = otp.getUserAccount();
        if (account.getStatus() != UserAccountStatus.ACTIVE) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "account_not_active");
        }

        account.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        account.setPasswordLoginEnabled(true);
        account.setUpdatedAt(now);
        otp.setUsedAt(now);
        otp.setUpdatedAt(now);
        userAccountRepository.save(account);
        passwordResetOtpRepository.save(otp);
        revokeActiveRefreshTokens(account.getId(), now);
    }

    @Override
    @Transactional(readOnly = true)
    public AuthUserResponse currentUser(Long userAccountId) {
        UserAccount account = userAccountRepository.findByIdWithRoles(userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "user_not_found"));
        return AuthUserResponse.from(account);
    }

    @Override
    @Transactional
    public void changePassword(Long userAccountId, ChangePasswordRequest request) {
        UserAccount account = userAccountRepository.findById(userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "user_not_found"));

        if (Boolean.FALSE.equals(account.getPasswordLoginEnabled())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "password_login_not_enabled");
        }
        if (!passwordEncoder.matches(request.currentPassword(), account.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_current_password");
        }

        Instant now = Instant.now();
        account.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        account.setPasswordLoginEnabled(true);
        account.setUpdatedAt(now);
        userAccountRepository.save(account);
    }

    @Override
    @Transactional
    public void createPassword(Long userAccountId, PasswordResetConfirmRequest request) {
        UserAccount account = userAccountRepository.findById(userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "user_not_found"));
        if (account.getStatus() != UserAccountStatus.ACTIVE) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "account_not_active");
        }
        if (!Boolean.FALSE.equals(account.getPasswordLoginEnabled())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "password_login_already_enabled");
        }
        if (!request.newPassword().equals(request.confirmPassword())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "password_confirmation_mismatch");
        }

        PasswordResetOtp otp = verifiedResetOtp(request.resetToken());
        if (!account.getId().equals(otp.getUserAccount().getId())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_reset_token");
        }

        Instant now = Instant.now();
        account.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        account.setPasswordLoginEnabled(true);
        account.setUpdatedAt(now);
        otp.setUsedAt(now);
        otp.setUpdatedAt(now);
        userAccountRepository.save(account);
        passwordResetOtpRepository.save(otp);
    }

    private AuthTokenResponse issueTokens(UserAccount account, String ipAddress, String userAgent) {
        String refreshToken = jwtService.createRefreshToken();
        String refreshHash = jwtService.hashToken(refreshToken);
        refreshTokenRepository.save(newRefreshToken(account, refreshHash, ipAddress, userAgent, Instant.now()));
        return new AuthTokenResponse(
                jwtService.createAccessToken(account),
                refreshToken,
                jwtService.accessTokenTtlSeconds(),
                AuthUserResponse.from(account)
        );
    }

    private PasswordResetOtp verifiedResetOtp(String resetToken) {
        String resetTokenHash = jwtService.hashToken(resetToken);
        PasswordResetOtp otp = passwordResetOtpRepository
                .findTopByResetTokenHashAndUsedAtIsNullOrderByCreatedAtDesc(resetTokenHash)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_reset_token"));
        Instant now = Instant.now();
        if (otp.getVerifiedAt() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_reset_token");
        }
        if (otp.getResetTokenExpiresAt() == null || !otp.getResetTokenExpiresAt().isAfter(now)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "reset_token_expired");
        }
        return otp;
    }

    private RefreshToken newRefreshToken(
            UserAccount account,
            String tokenHash,
            String ipAddress,
            String userAgent,
            Instant now
    ) {
        RefreshToken token = new RefreshToken();
        token.setUserAccount(account);
        token.setTokenHash(tokenHash);
        token.setStatus(RefreshTokenStatus.ACTIVE);
        token.setIssuedAt(now);
        token.setExpiresAt(jwtService.refreshTokenExpiresAt());
        token.setIpAddress(trimToLength(blankToNull(ipAddress), 45));
        token.setUserAgent(blankToNull(userAgent));
        token.setCreatedAt(now);
        token.setUpdatedAt(now);
        return token;
    }

    private UserAccount updateExistingGoogleAccount(
            UserAccount account,
            String fullName,
            String avatarUrl,
            Instant now
    ) {
        String normalizedName = blankToNull(fullName);
        if (blankToNull(account.getFullName()) == null && normalizedName != null) {
            account.setFullName(normalizedName);
        }
        if (blankToNull(account.getDisplayName()) == null && normalizedName != null) {
            account.setDisplayName(normalizedName);
        }
        account.setEmailVerified(true);
        ensureCustomerRole(account);
        ensureCustomerProfile(account, now, avatarUrl);
        return account;
    }

    private UserAccount createGoogleCustomer(
            String email,
            String fullName,
            String avatarUrl,
            Instant now
    ) {
        String normalizedName = blankToNull(fullName);
        UserAccount account = new UserAccount();
        account.setEmail(email);
        account.setPasswordHash(passwordEncoder.encode("GOOGLE:" + createResetToken()));
        account.setPasswordLoginEnabled(false);
        account.setFullName(normalizedName);
        account.setDisplayName(normalizedName);
        account.setStatus(UserAccountStatus.ACTIVE);
        account.setEmailVerified(true);
        account.setPhoneVerified(false);
        account.setCreatedAt(now);
        account.setUpdatedAt(now);
        ensureCustomerRole(account);

        UserAccount saved = userAccountRepository.save(account);
        createCustomerProfile(saved, now, avatarUrl);
        return saved;
    }

    private void ensureCustomerProfile(UserAccount account, Instant now, String avatarUrl) {
        customerProfileRepository.findByUserAccount_Id(account.getId())
                .ifPresentOrElse(profile -> {
                    String normalizedAvatar = blankToNull(avatarUrl);
                    if (blankToNull(profile.getAvatarUrl()) == null && normalizedAvatar != null) {
                        profile.setAvatarUrl(normalizedAvatar);
                        profile.setUpdatedAt(now);
                        customerProfileRepository.save(profile);
                    }
                }, () -> createCustomerProfile(account, now, avatarUrl));
    }

    private void sendPasswordResetEmail(UserAccount account, String rawOtp) {
        if (mailSender == null) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "email_service_unavailable");
        }
        SimpleMailMessage message = new SimpleMailMessage();
        String from = mailFrom != null ? mailFrom : mailUsername;
        if (from != null) {
            message.setFrom(from);
        }
        message.setTo(account.getEmail());
        message.setSubject("Ma OTP dat lai mat khau");
        message.setText("""
                Ma OTP dat lai mat khau cua ban la: %s

                Ma nay co hieu luc trong %d phut. Neu ban khong yeu cau dat lai mat khau, vui long bo qua email nay.
                """.formatted(rawOtp, otpTtlMinutes));
        try {
            mailSender.send(message);
        } catch (Exception exception) {
            log.warn("password_reset_email_failed user_id={} email={}", account.getId(), account.getEmail(), exception);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "otp_email_send_failed");
        }
    }

    private void ensureOtpCanBeChecked(PasswordResetOtp otp, Instant now) {
        if (!otp.getExpiresAt().isAfter(now)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "otp_expired");
        }
        if (otp.getFailedAttempts() >= otp.getMaxFailedAttempts()) {
            throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "otp_attempts_exceeded");
        }
    }

    private void revokeActiveRefreshTokens(Long userAccountId, Instant now) {
        List<RefreshToken> activeTokens = refreshTokenRepository
                .findByUserAccount_IdAndStatusOrderByExpiresAtDesc(userAccountId, RefreshTokenStatus.ACTIVE);
        activeTokens.forEach(token -> {
            token.setStatus(RefreshTokenStatus.REVOKED);
            token.setRevokedAt(now);
            token.setUpdatedAt(now);
        });
        refreshTokenRepository.saveAll(activeTokens);
    }

    private String generateOtp() {
        return "%06d".formatted(secureRandom.nextInt(1_000_000));
    }

    private String createResetToken() {
        byte[] bytes = new byte[RESET_TOKEN_BYTES];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private void createCustomerProfile(UserAccount account, Instant now) {
        createCustomerProfile(account, now, null);
    }

    private void createCustomerProfile(UserAccount account, Instant now, String avatarUrl) {
        CustomerProfile profile = new CustomerProfile();
        profile.setUserAccount(account);
        profile.setAvatarUrl(blankToNull(avatarUrl));
        profile.setLoyaltyPoints(0);
        profile.setMarketingOptIn(false);
        profile.setCreatedAt(now);
        profile.setUpdatedAt(now);
        customerProfileRepository.save(profile);
    }

    private void ensureCustomerRole(UserAccount account) {
        boolean hasCustomerRole = account.getRoles().stream()
                .anyMatch(role -> ROLE_CUSTOMER.equals(role.getName()));
        if (!hasCustomerRole) {
            account.getRoles().add(customerRole());
        }
    }

    private UserRole customerRole() {
        return userRoleRepository.findByName(ROLE_CUSTOMER)
                .orElseGet(() -> {
                    UserRole role = new UserRole();
                    role.setName(ROLE_CUSTOMER);
                    role.setDescription("Default customer role");
                    role.setActive(true);
                    role.setCreatedAt(Instant.now());
                    role.setUpdatedAt(Instant.now());
                    return userRoleRepository.save(role);
                });
    }

    private static String normalizeEmail(String email) {
        return email == null ? null : email.trim().toLowerCase(Locale.ROOT);
    }

    private static String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private static String trimToLength(String value, int maxLength) {
        if (value == null || value.length() <= maxLength) {
            return value;
        }
        return value.substring(0, maxLength);
    }

    private static ResponseStatusException unauthorized(String reason) {
        return new ResponseStatusException(HttpStatus.UNAUTHORIZED, reason);
    }
}
