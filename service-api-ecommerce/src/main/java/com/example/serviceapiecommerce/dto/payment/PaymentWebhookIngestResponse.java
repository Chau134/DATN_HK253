package com.example.serviceapiecommerce.dto.payment;

import com.example.serviceapiecommerce.entity.PaymentWebhookEventStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record PaymentWebhookIngestResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("provider")
        String provider,

        @JsonProperty("event_id")
        String eventId,

        @JsonProperty("event_type")
        String eventType,

        @JsonProperty("processing_status")
        PaymentWebhookEventStatus processingStatus,

        @JsonProperty("duplicate")
        boolean duplicate,

        @JsonProperty("received_at")
        Instant receivedAt,

        @JsonProperty("processed_at")
        Instant processedAt
) {
}
