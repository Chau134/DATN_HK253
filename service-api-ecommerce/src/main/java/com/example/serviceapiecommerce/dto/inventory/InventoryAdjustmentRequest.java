package com.example.serviceapiecommerce.dto.inventory;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Size;

public record InventoryAdjustmentRequest(
        @JsonProperty("quantity_delta")
        Integer quantityDelta,

        @JsonProperty("idempotency_key")
        @Size(max = 100)
        String idempotencyKey,

        @JsonProperty("reason")
        @Size(max = 150)
        String reason,

        @JsonProperty("note")
        @Size(max = 2000)
        String note
) {
}
