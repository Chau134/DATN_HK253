package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.catalog.CatalogCategoryResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogPageResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductDetailResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductListItemResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductSearchRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionResponse;
import com.example.serviceapiecommerce.entity.PromotionStatus;
import com.example.serviceapiecommerce.service.CatalogService;
import com.example.serviceapiecommerce.service.PromotionService;
import java.math.BigDecimal;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class CatalogController {
    private final CatalogService catalogService;
    private final PromotionService promotionService;

    public CatalogController(CatalogService catalogService, PromotionService promotionService) {
        this.catalogService = catalogService;
        this.promotionService = promotionService;
    }

    @GetMapping("/products")
    public CatalogPageResponse<CatalogProductListItemResponse> products(
            @RequestParam(name = "category_id", required = false) Long categoryId,
            @RequestParam(required = false) String gender,
            @RequestParam(required = false) String brand,
            @RequestParam(name = "min_price", required = false) BigDecimal minPrice,
            @RequestParam(name = "max_price", required = false) BigDecimal maxPrice,
            @RequestParam(required = false) Boolean available,
            @RequestParam(required = false) String keyword,
            @RequestParam(name = "q", required = false) String q,
            @RequestParam(required = false) Integer page,
            @RequestParam(required = false) Integer size,
            @RequestParam(required = false) String sort
    ) {
        return catalogService.findProducts(new CatalogProductSearchRequest(
                categoryId,
                gender,
                brand,
                minPrice,
                maxPrice,
                available,
                hasText(keyword) ? keyword : q,
                page,
                size,
                sort
        ));
    }

    @GetMapping("/products/{productId}")
    public CatalogProductDetailResponse product(@PathVariable Long productId) {
        return catalogService.getProduct(productId);
    }

    @GetMapping("/categories")
    public List<CatalogCategoryResponse> categories() {
        return catalogService.getActiveCategories();
    }

    @GetMapping("/brands")
    public List<String> brands() {
        return catalogService.getBrandNames();
    }

    @GetMapping("/promotions")
    public List<PromotionResponse> promotions() {
        return promotionService.listPromotions(PromotionStatus.ACTIVE);
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
