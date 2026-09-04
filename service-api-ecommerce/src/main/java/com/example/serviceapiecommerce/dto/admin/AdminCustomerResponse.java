package com.example.serviceapiecommerce.dto.admin;

import com.example.serviceapiecommerce.entity.UserAccount;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

public record AdminCustomerResponse(
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

        @JsonProperty("roles")
        List<String> roles,

        @JsonProperty("created_at")
        Instant createdAt
) {
    public static AdminCustomerResponse from(UserAccount account) {
        List<String> roleNames = account.getRoles().stream()
                .filter(role -> role.getActive() == null || role.getActive())
                .map(role -> role.getName())
                .sorted()
                .toList();
        return new AdminCustomerResponse(
                account.getId(),
                account.getEmail(),
                account.getPhoneNumber(),
                account.getFullName(),
                account.getDisplayName(),
                account.getStatus() == null ? null : account.getStatus().name(),
                roleNames,
                account.getCreatedAt()
        );
    }
}
