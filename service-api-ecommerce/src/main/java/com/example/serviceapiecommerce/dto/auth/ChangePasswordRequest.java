package com.example.serviceapiecommerce.dto.auth;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ChangePasswordRequest(
        @JsonProperty("current_password")
        @NotBlank(message = "Mật khẩu hiện tại không được để trống")
        String currentPassword,

        @JsonProperty("new_password")
        @NotBlank(message = "Mật khẩu mới không được để trống")
        @Size(min = 8, max = 100, message = "Mật khẩu mới phải từ 8 đến 100 ký tự")
        String newPassword
) {
}
