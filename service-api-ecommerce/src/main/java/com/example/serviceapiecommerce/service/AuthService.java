package com.example.serviceapiecommerce.service;

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

public interface AuthService {
    AuthTokenResponse register(RegisterRequest request, String ipAddress, String userAgent);

    AuthTokenResponse login(LoginRequest request, String ipAddress, String userAgent);

    AuthTokenResponse loginWithGoogleOAuth(
            String email,
            String fullName,
            String avatarUrl,
            String ipAddress,
            String userAgent
    );

    AuthTokenResponse refresh(RefreshTokenRequest request, String ipAddress, String userAgent);

    void logout(LogoutRequest request);

    void requestPasswordReset(PasswordResetRequest request);

    PasswordResetVerifyResponse verifyPasswordResetOtp(PasswordResetVerifyRequest request);

    void confirmPasswordReset(PasswordResetConfirmRequest request);

    AuthUserResponse currentUser(Long userAccountId);

    void changePassword(Long userAccountId, ChangePasswordRequest request);

    void createPassword(Long userAccountId, PasswordResetConfirmRequest request);
}
