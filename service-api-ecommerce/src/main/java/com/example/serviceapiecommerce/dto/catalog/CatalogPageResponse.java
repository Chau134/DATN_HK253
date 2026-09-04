package com.example.serviceapiecommerce.dto.catalog;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import org.springframework.data.domain.Page;

public record CatalogPageResponse<T>(
        @JsonProperty("items")
        List<T> items,

        @JsonProperty("page")
        int page,

        @JsonProperty("size")
        int size,

        @JsonProperty("total_elements")
        long totalElements,

        @JsonProperty("total_pages")
        int totalPages,

        @JsonProperty("first")
        boolean first,

        @JsonProperty("last")
        boolean last,

        @JsonProperty("sort")
        String sort
) {
    public CatalogPageResponse {
        items = items == null ? List.of() : List.copyOf(items);
    }

    public static <T> CatalogPageResponse<T> from(Page<T> page, String sort) {
        return new CatalogPageResponse<>(
                page.getContent(),
                page.getNumber(),
                page.getSize(),
                page.getTotalElements(),
                page.getTotalPages(),
                page.isFirst(),
                page.isLast(),
                sort
        );
    }
}
