package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiIndexSingleResponse(
        @JsonProperty("product_id")
        String productId,

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
    public AiIndexSingleResponse {
        indexedCount = indexedCount == null ? 0 : indexedCount;
        failedCount = failedCount == null ? 0 : failedCount;
        imageIndexedCount = imageIndexedCount == null ? 0 : imageIndexedCount;
        imageFailedCount = imageFailedCount == null ? 0 : imageFailedCount;
        failures = failures == null ? List.of() : List.copyOf(failures);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }

    public static AiIndexSingleResponse fromBatch(String productId, AiIndexBatchResponse response) {
        return new AiIndexSingleResponse(
                productId,
                response.indexedCount(),
                response.failedCount(),
                response.imageIndexedCount(),
                response.imageFailedCount(),
                response.failures(),
                response.warnings()
        );
    }

    public static AiIndexSingleResponse unavailable(String productId, String warning) {
        return new AiIndexSingleResponse(
                productId,
                0,
                1,
                0,
                0,
                List.of(new AiIndexFailureDto(productId, "request", warning, null)),
                List.of(warning)
        );
    }
}
