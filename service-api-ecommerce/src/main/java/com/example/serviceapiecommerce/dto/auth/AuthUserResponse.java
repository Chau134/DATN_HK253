package com.example.serviceapiecommerce.dto.auth;

import com.example.serviceapiecommerce.entity.UserAccount;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AuthUserResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("email")
        String email,

        @JsonProperty("phone_number")
        String phoneNumber,

        @JsonProperty("full_name")
        String fullName,

        @JsonProperty("display_name")
        String displayName,

        @JsonProperty("status")
        String status,

        @JsonProperty("password_login_enabled")
        Boolean passwordLoginEnabled,

        @JsonProperty("roles")
        List<String> roles
) {
    public static AuthUserResponse from(UserAccount account) {
        List<String> roleNames = account.getRoles().stream()
                .filter(role -> role.getActive() == null || role.getActive())
                .map(role -> role.getName())
                .sorted()
                .toList();
        return new AuthUserResponse(
                account.getId(),
                account.getEmail(),
                account.getPhoneNumber(),
                account.getFullName(),
                account.getDisplayName(),
                account.getStatus() == null ? null : account.getStatus().name(),
                !Boolean.FALSE.equals(account.getPasswordLoginEnabled()),
                roleNames
        );
    }
}
