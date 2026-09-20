package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.Valid;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;

public record AiHybridSearchRequest(
        @JsonProperty("query")
        @Size(max = 1000)
        String query,

        @JsonProperty("image")
        Map<String, Object> image,

        @JsonProperty("crop_box")
        @Valid
        AiImageBoundingBoxDto cropBox,

        @JsonProperty("crop_boxes")
        @Valid
        @Size(min = 1, max = 20)
        List<AiImageBoundingBoxDto> cropBoxes,

        @JsonProperty("filters")
        @Valid
        AiSearchFilterDto filters,

        @JsonProperty("top_k")
        @Min(1)
        @Max(100)
        Integer topK,

        @JsonProperty("strategy")
        @Size(max = 50)
        String strategy
) {
    @JsonIgnore
    @AssertTrue(message = "crop_box and crop_boxes cannot be used together")
    public boolean isCropSelectionValid() {
        return cropBox == null || cropBoxes == null;
    }

    public AiHybridSearchRequest(
            String query,
            Map<String, Object> image,
            AiImageBoundingBoxDto cropBox,
            AiSearchFilterDto filters,
            Integer topK,
            String strategy
    ) {
        this(query, image, cropBox, null, filters, topK, strategy);
    }
}
