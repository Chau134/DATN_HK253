package com.example.serviceapiecommerce.dto.ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;

public record AiProductContextRequest(
        @JsonProperty("product_ids")
        @NotEmpty
        @Size(max = 20)
        List<@NotBlank String> productIds
) {
    public AiProductContextRequest {
        productIds = productIds == null ? List.of() : List.copyOf(productIds);
    }
}
