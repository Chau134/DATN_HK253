package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.admin.AdminCategoryRequest;
import com.example.serviceapiecommerce.dto.admin.AdminCategoryResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductImageRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductImageResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductAttributeRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductAttributeResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductPriceRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductPriceResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductVariantRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductVariantResponse;
import java.util.List;

public interface AdminCatalogService {
    List<AdminCategoryResponse> listCategories(Boolean active);

    AdminCategoryResponse createCategory(AdminCategoryRequest request);

    AdminCategoryResponse updateCategory(Long categoryId, AdminCategoryRequest request);

    void archiveCategory(Long categoryId);

    List<AdminProductResponse> listProducts();

    AdminProductResponse getProduct(Long productId);

    AdminProductResponse createProduct(AdminProductRequest request);

    AdminProductResponse updateProduct(Long productId, AdminProductRequest request);

    void deleteProduct(Long productId);

    AdminProductResponse addProductCategory(Long productId, Long categoryId);

    AdminProductResponse removeProductCategory(Long productId, Long categoryId);

    AdminProductVariantResponse createVariant(Long productId, AdminProductVariantRequest request);

    AdminProductVariantResponse updateVariant(Long productId, Long variantId, AdminProductVariantRequest request);

    void deleteVariant(Long productId, Long variantId);

    AdminProductPriceResponse addPrice(Long productId, AdminProductPriceRequest request);

    AdminProductImageResponse addImage(Long productId, AdminProductImageRequest request);

    void deleteImage(Long productId, Long imageId);

    AdminProductAttributeResponse addAttribute(Long productId, AdminProductAttributeRequest request);

    AdminProductAttributeResponse updateAttribute(Long productId, Long attributeId, AdminProductAttributeRequest request);

    void deleteAttribute(Long productId, Long attributeId);
}
