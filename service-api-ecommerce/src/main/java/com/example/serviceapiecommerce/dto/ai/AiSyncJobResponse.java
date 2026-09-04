package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record AiSyncJobResponse(
        @JsonProperty("job_id")
        String jobId,

        @JsonProperty("status")
        String status,

        @JsonProperty("requested_limit")
        Integer requestedLimit,

        @JsonProperty("result")
        AiSyncResponse result,

        @JsonProperty("error")
        String error,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("started_at")
        Instant startedAt,

        @JsonProperty("completed_at")
        Instant completedAt
) {
}
