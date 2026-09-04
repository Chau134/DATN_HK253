package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

public record AiSyncResponse(
        @JsonProperty("sync_name")
        String syncName,

        @JsonProperty("sync_type")
        String syncType,

        @JsonProperty("total_count")
        Long totalCount,

        @JsonProperty("success_count")
        Long successCount,

        @JsonProperty("failure_count")
        Long failureCount,

        @JsonProperty("batch_count")
        Integer batchCount,

        @JsonProperty("image_indexed_count")
        Long imageIndexedCount,

        @JsonProperty("image_failure_count")
        Long imageFailureCount,

        @JsonProperty("failed_product_ids")
        List<String> failedProductIds,

        @JsonProperty("warnings")
        List<String> warnings,

        @JsonProperty("last_successful_ai_sync_at")
        Instant lastSuccessfulAiSyncAt,

        @JsonProperty("new_last_successful_ai_sync_at")
        Instant newLastSuccessfulAiSyncAt
) {
    public AiSyncResponse {
        totalCount = totalCount == null ? 0L : totalCount;
        successCount = successCount == null ? 0L : successCount;
        failureCount = failureCount == null ? 0L : failureCount;
        batchCount = batchCount == null ? 0 : batchCount;
        imageIndexedCount = imageIndexedCount == null ? 0L : imageIndexedCount;
        imageFailureCount = imageFailureCount == null ? 0L : imageFailureCount;
        failedProductIds = failedProductIds == null ? List.of() : List.copyOf(failedProductIds);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }
}
