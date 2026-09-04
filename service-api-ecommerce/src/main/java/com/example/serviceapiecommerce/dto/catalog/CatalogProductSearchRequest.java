package com.example.serviceapiecommerce.dto.catalog;

import java.math.BigDecimal;

public record CatalogProductSearchRequest(
        Long categoryId,
        String gender,
        String brand,
        BigDecimal minPrice,
        BigDecimal maxPrice,
        Boolean available,
        String keyword,
        Integer page,
        Integer size,
        String sort
) {
}
