package com.example.serviceapiecommerce.dto.wishlist;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record WishlistCreateRequest(
        @JsonProperty("name")
        @NotBlank
        @Size(max = 100)
        String name
) {
}
