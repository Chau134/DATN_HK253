package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.auth.AuthTokenResponse;
import com.example.serviceapiecommerce.dto.auth.LoginRequest;
import com.example.serviceapiecommerce.dto.auth.LogoutRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetConfirmRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetVerifyRequest;
import com.example.serviceapiecommerce.dto.auth.PasswordResetVerifyResponse;
import com.example.serviceapiecommerce.dto.auth.RefreshTokenRequest;
import com.example.serviceapiecommerce.dto.auth.RegisterRequest;
import com.example.serviceapiecommerce.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private static final Logger log = LoggerFactory.getLogger(AuthController.class);

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/register")
    public ResponseEntity<AuthTokenResponse> register(
            @Valid @RequestBody RegisterRequest request,
            HttpServletRequest servletRequest
    ) {
        AuthTokenResponse response = authService.register(request, clientIp(servletRequest), userAgent(servletRequest));
        log.info("auth_register_success user_id={} ip={}", response.user().id(), clientIp(servletRequest));
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(response);
    }

    @PostMapping("/login")
    public AuthTokenResponse login(
            @Valid @RequestBody LoginRequest request,
            HttpServletRequest servletRequest
    ) {
        AuthTokenResponse response = authService.login(request, clientIp(servletRequest), userAgent(servletRequest));
        log.info("auth_login_success user_id={} ip={}", response.user().id(), clientIp(servletRequest));
        return response;
    }

    @PostMapping("/refresh")
    public AuthTokenResponse refresh(
            @Valid @RequestBody RefreshTokenRequest request,
            HttpServletRequest servletRequest
    ) {
        AuthTokenResponse response = authService.refresh(request, clientIp(servletRequest), userAgent(servletRequest));
        log.info("auth_refresh_success user_id={} ip={}", response.user().id(), clientIp(servletRequest));
        return response;
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(@Valid @RequestBody LogoutRequest request) {
        authService.logout(request);
        log.info("auth_logout_success");
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/password-reset/request")
    public ResponseEntity<Void> requestPasswordReset(@Valid @RequestBody PasswordResetRequest request) {
        authService.requestPasswordReset(request);
        log.info("password_reset_requested email={}", request.email());
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/password-reset/verify")
    public PasswordResetVerifyResponse verifyPasswordResetOtp(
            @Valid @RequestBody PasswordResetVerifyRequest request
    ) {
        PasswordResetVerifyResponse response = authService.verifyPasswordResetOtp(request);
        log.info("password_reset_otp_verified email={}", request.email());
        return response;
    }

    @PostMapping("/password-reset/confirm")
    public ResponseEntity<Void> confirmPasswordReset(@Valid @RequestBody PasswordResetConfirmRequest request) {
        authService.confirmPasswordReset(request);
        log.info("password_reset_confirmed");
        return ResponseEntity.noContent().build();
    }

    private static String clientIp(HttpServletRequest request) {
        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (forwardedFor != null && !forwardedFor.isBlank()) {
            return forwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    private static String userAgent(HttpServletRequest request) {
        return request.getHeader("User-Agent");
    }
}
