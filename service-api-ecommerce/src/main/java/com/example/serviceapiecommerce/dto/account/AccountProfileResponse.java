package com.example.serviceapiecommerce.dto.account;

import com.example.serviceapiecommerce.entity.CustomerProfile;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDate;
import java.util.List;

public record AccountProfileResponse(
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
        List<String> roles,

        @JsonProperty("first_name")
        String firstName,

        @JsonProperty("last_name")
        String lastName,

        @JsonProperty("gender")
        String gender,

        @JsonProperty("date_of_birth")
        LocalDate dateOfBirth,

        @JsonProperty("avatar_url")
        String avatarUrl,

        @JsonProperty("loyalty_points")
        Integer loyaltyPoints,

        @JsonProperty("marketing_opt_in")
        Boolean marketingOptIn
) {
    public static AccountProfileResponse from(UserAccount account, CustomerProfile profile) {
        List<String> roleNames = account.getRoles().stream()
                .filter(role -> role.getActive() == null || role.getActive())
                .map(role -> role.getName())
                .sorted()
                .toList();

        return new AccountProfileResponse(
                account.getId(),
                account.getEmail(),
                account.getPhoneNumber(),
                account.getFullName(),
                account.getDisplayName(),
                account.getStatus() == null ? null : account.getStatus().name(),
                !Boolean.FALSE.equals(account.getPasswordLoginEnabled()),
                roleNames,
                profile == null ? null : profile.getFirstName(),
                profile == null ? null : profile.getLastName(),
                profile == null ? null : profile.getGender(),
                profile == null ? null : profile.getDateOfBirth(),
                profile == null ? null : profile.getAvatarUrl(),
                profile == null ? 0 : profile.getLoyaltyPoints(),
                profile != null && Boolean.TRUE.equals(profile.getMarketingOptIn())
        );
    }
}
