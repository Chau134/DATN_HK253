package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiProductIndexBatchRequest(
        @JsonProperty("items")
        List<AiProductIndexItemDto> items
) {
}
