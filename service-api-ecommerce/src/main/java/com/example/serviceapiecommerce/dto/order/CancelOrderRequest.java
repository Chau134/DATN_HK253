package com.example.serviceapiecommerce.dto.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Size;

public record CancelOrderRequest(
        @JsonProperty("reason")
        @Size(max = 150)
        String reason,

        @JsonProperty("note")
        @Size(max = 2000)
        String note
) {
}
