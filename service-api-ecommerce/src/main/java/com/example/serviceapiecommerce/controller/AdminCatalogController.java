package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.admin.AdminCategoryRequest;
import com.example.serviceapiecommerce.dto.admin.AdminCategoryResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductAttributeRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductAttributeResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductImageRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductImageResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductImageUploadResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductPriceRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductPriceResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductVariantRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductVariantResponse;
import com.example.serviceapiecommerce.service.AdminCatalogService;
import com.example.serviceapiecommerce.service.CloudinaryAvatarUploadService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/admin/catalog")
public class AdminCatalogController {
    private final AdminCatalogService adminCatalogService;
    private final CloudinaryAvatarUploadService cloudinaryAvatarUploadService;

    public AdminCatalogController(
            AdminCatalogService adminCatalogService,
            CloudinaryAvatarUploadService cloudinaryAvatarUploadService
    ) {
        this.adminCatalogService = adminCatalogService;
        this.cloudinaryAvatarUploadService = cloudinaryAvatarUploadService;
    }

    @GetMapping("/categories")
    public List<AdminCategoryResponse> categories(@RequestParam(required = false) Boolean active) {
        return adminCatalogService.listCategories(active);
    }

    @PostMapping("/categories")
    @ResponseStatus(HttpStatus.CREATED)
    public AdminCategoryResponse createCategory(@Valid @RequestBody AdminCategoryRequest request) {
        return adminCatalogService.createCategory(request);
    }

    @PutMapping("/categories/{categoryId}")
    public AdminCategoryResponse updateCategory(
            @PathVariable Long categoryId,
            @Valid @RequestBody AdminCategoryRequest request
    ) {
        return adminCatalogService.updateCategory(categoryId, request);
    }

    @DeleteMapping("/categories/{categoryId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void archiveCategory(@PathVariable Long categoryId) {
        adminCatalogService.archiveCategory(categoryId);
    }

    @GetMapping("/products")
    public List<AdminProductResponse> products() {
        return adminCatalogService.listProducts();
    }

    @PostMapping("/products")
    @ResponseStatus(HttpStatus.CREATED)
    public AdminProductResponse createProduct(@Valid @RequestBody AdminProductRequest request) {
        return adminCatalogService.createProduct(request);
    }

    @GetMapping("/products/{productId}")
    public AdminProductResponse product(@PathVariable Long productId) {
        return adminCatalogService.getProduct(productId);
    }

    @PutMapping("/products/{productId}")
    public AdminProductResponse updateProduct(
            @PathVariable Long productId,
            @Valid @RequestBody AdminProductRequest request
    ) {
        return adminCatalogService.updateProduct(productId, request);
    }

    @DeleteMapping("/products/{productId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteProduct(@PathVariable Long productId) {
        adminCatalogService.deleteProduct(productId);
    }

    @PostMapping("/products/{productId}/categories/{categoryId}")
    public AdminProductResponse addProductCategory(
            @PathVariable Long productId,
            @PathVariable Long categoryId
    ) {
        return adminCatalogService.addProductCategory(productId, categoryId);
    }

    @DeleteMapping("/products/{productId}/categories/{categoryId}")
    public AdminProductResponse removeProductCategory(
            @PathVariable Long productId,
            @PathVariable Long categoryId
    ) {
        return adminCatalogService.removeProductCategory(productId, categoryId);
    }

    @PostMapping("/products/{productId}/variants")
    @ResponseStatus(HttpStatus.CREATED)
    public AdminProductVariantResponse createVariant(
            @PathVariable Long productId,
            @Valid @RequestBody AdminProductVariantRequest request
    ) {
        return adminCatalogService.createVariant(productId, request);
    }

    @PutMapping("/products/{productId}/variants/{variantId}")
    public AdminProductVariantResponse updateVariant(
            @PathVariable Long productId,
            @PathVariable Long variantId,
            @Valid @RequestBody AdminProductVariantRequest request
    ) {
        return adminCatalogService.updateVariant(productId, variantId, request);
    }

    @DeleteMapping("/products/{productId}/variants/{variantId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteVariant(
            @PathVariable Long productId,
            @PathVariable Long variantId
    ) {
        adminCatalogService.deleteVariant(productId, variantId);
    }

    @PostMapping("/products/{productId}/prices")
    @ResponseStatus(HttpStatus.CREATED)
    public AdminProductPriceResponse addPrice(
            @PathVariable Long productId,
            @Valid @RequestBody AdminProductPriceRequest request
    ) {
        return adminCatalogService.addPrice(productId, request);
    }

    @PostMapping("/products/{productId}/images")
    @ResponseStatus(HttpStatus.CREATED)
    public AdminProductImageResponse addImage(
            @PathVariable Long productId,
            @Valid @RequestBody AdminProductImageRequest request
    ) {
        return adminCatalogService.addImage(productId, request);
    }

    @PostMapping(value = "/products/{productId}/images/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public AdminProductImageUploadResponse uploadImage(
            @PathVariable Long productId,
            @RequestPart("file") MultipartFile file
    ) {
        adminCatalogService.getProduct(productId);
        return new AdminProductImageUploadResponse(cloudinaryAvatarUploadService.uploadProductImage(productId, file));
    }

    @DeleteMapping("/products/{productId}/images/{imageId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteImage(
            @PathVariable Long productId,
            @PathVariable Long imageId
    ) {
        adminCatalogService.deleteImage(productId, imageId);
    }

    @PostMapping("/products/{productId}/attributes")
    @ResponseStatus(HttpStatus.CREATED)
    public AdminProductAttributeResponse addAttribute(
            @PathVariable Long productId,
            @Valid @RequestBody AdminProductAttributeRequest request
    ) {
        return adminCatalogService.addAttribute(productId, request);
    }

    @PutMapping("/products/{productId}/attributes/{attributeId}")
    public AdminProductAttributeResponse updateAttribute(
            @PathVariable Long productId,
            @PathVariable Long attributeId,
            @Valid @RequestBody AdminProductAttributeRequest request
    ) {
        return adminCatalogService.updateAttribute(productId, attributeId, request);
    }

    @DeleteMapping("/products/{productId}/attributes/{attributeId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAttribute(
            @PathVariable Long productId,
            @PathVariable Long attributeId
    ) {
        adminCatalogService.deleteAttribute(productId, attributeId);
    }
}
