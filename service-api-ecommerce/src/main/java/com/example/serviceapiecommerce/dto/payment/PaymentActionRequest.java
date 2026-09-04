package com.example.serviceapiecommerce.dto.payment;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Size;

public record PaymentActionRequest(
        @JsonProperty("idempotency_key")
        @Size(max = 100)
        String idempotencyKey,

        @JsonProperty("reason")
        @Size(max = 150)
        String reason,

        @JsonProperty("failure_code")
        @Size(max = 100)
        String failureCode,

        @JsonProperty("failure_message")
        @Size(max = 255)
        String failureMessage,

        @JsonProperty("note")
        @Size(max = 2000)
        String note
) {
}
