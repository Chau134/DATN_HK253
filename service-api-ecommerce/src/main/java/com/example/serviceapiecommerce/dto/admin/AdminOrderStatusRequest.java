package com.example.serviceapiecommerce.dto.admin;

import com.example.serviceapiecommerce.entity.OrderStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record AdminOrderStatusRequest(
        @JsonProperty("status")
        @NotNull
        OrderStatus status,

        @JsonProperty("reason")
        @Size(max = 150)
        String reason,

        @JsonProperty("note")
        @Size(max = 2000)
        String note
) {
}
