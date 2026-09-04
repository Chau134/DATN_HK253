package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiIndexBatchResponse(
        @JsonProperty("indexed_count")
        Integer indexedCount,

        @JsonProperty("failed_count")
        Integer failedCount,

        @JsonProperty("image_indexed_count")
        Integer imageIndexedCount,

        @JsonProperty("image_failed_count")
        Integer imageFailedCount,

        @JsonProperty("failures")
        List<AiIndexFailureDto> failures,

        @JsonProperty("warnings")
        List<String> warnings
) {
    public AiIndexBatchResponse {
        indexedCount = indexedCount == null ? 0 : indexedCount;
        failedCount = failedCount == null ? 0 : failedCount;
        imageIndexedCount = imageIndexedCount == null ? 0 : imageIndexedCount;
        imageFailedCount = imageFailedCount == null ? 0 : imageFailedCount;
        failures = failures == null ? List.of() : List.copyOf(failures);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }

    public static AiIndexBatchResponse unavailable(int failedCount, String warning) {
        return new AiIndexBatchResponse(
                0,
                Math.max(failedCount, 0),
                0,
                0,
                List.of(new AiIndexFailureDto(null, "request", warning, null)),
                List.of(warning)
        );
    }
}
