package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.catalog.CatalogCategoryResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogPageResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductDetailResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductListItemResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductSearchRequest;
import java.util.List;

public interface CatalogService {
    CatalogPageResponse<CatalogProductListItemResponse> findProducts(CatalogProductSearchRequest request);

    CatalogProductDetailResponse getProduct(Long productId);

    List<CatalogProductDetailResponse> getProductsByIds(List<Long> productIds);

    List<CatalogCategoryResponse> getActiveCategories();

    List<String> getBrandNames();
}
