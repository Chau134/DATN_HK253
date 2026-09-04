package com.example.serviceapiecommerce.dto.inventory;

import com.example.serviceapiecommerce.entity.InventoryMovementType;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record InventoryMovementResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("product_id")
        Long productId,

        @JsonProperty("product_variant_id")
        Long productVariantId,

        @JsonProperty("movement_type")
        InventoryMovementType movementType,

        @JsonProperty("quantity_delta")
        Integer quantityDelta,

        @JsonProperty("quantity_before")
        Integer quantityBefore,

        @JsonProperty("quantity_after")
        Integer quantityAfter,

        @JsonProperty("reference_type")
        String referenceType,

        @JsonProperty("reference_id")
        String referenceId,

        @JsonProperty("idempotency_key")
        String idempotencyKey,

        @JsonProperty("reason")
        String reason,

        @JsonProperty("note")
        String note,

        @JsonProperty("created_at")
        Instant createdAt
) {
}
