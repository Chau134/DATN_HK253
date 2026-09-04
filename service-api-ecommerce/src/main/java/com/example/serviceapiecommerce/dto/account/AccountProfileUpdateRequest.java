package com.example.serviceapiecommerce.dto.account;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Size;
import java.time.LocalDate;

public record AccountProfileUpdateRequest(
        @JsonProperty("email")
        @Email
        @Size(max = 320)
        String email,

        @JsonProperty("phone_number")
        @Size(max = 30)
        String phoneNumber,

        @JsonProperty("full_name")
        @Size(max = 150)
        String fullName,

        @JsonProperty("display_name")
        @Size(max = 150)
        String displayName,

        @JsonProperty("first_name")
        @Size(max = 100)
        String firstName,

        @JsonProperty("last_name")
        @Size(max = 100)
        String lastName,

        @JsonProperty("gender")
        @Size(max = 50)
        String gender,

        @JsonProperty("date_of_birth")
        LocalDate dateOfBirth,

        @JsonProperty("marketing_opt_in")
        Boolean marketingOptIn
) {
}
