package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.promotion.AdminPromotionRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionCategoryRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionCategoryResponse;
import com.example.serviceapiecommerce.dto.promotion.PromotionProductRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionProductResponse;
import com.example.serviceapiecommerce.dto.promotion.PromotionResponse;
import com.example.serviceapiecommerce.entity.PromotionStatus;
import com.example.serviceapiecommerce.service.PromotionService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/promotions")
public class AdminPromotionController {
    private final PromotionService promotionService;

    public AdminPromotionController(PromotionService promotionService) {
        this.promotionService = promotionService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public PromotionResponse createPromotion(@Valid @RequestBody AdminPromotionRequest request) {
        return promotionService.createPromotion(request);
    }

    @GetMapping
    public List<PromotionResponse> promotions(@RequestParam(required = false) PromotionStatus status) {
        return promotionService.listPromotions(status);
    }

    @GetMapping("/{promotionId}")
    public PromotionResponse promotion(@PathVariable Long promotionId) {
        return promotionService.getPromotion(promotionId);
    }

    @PutMapping("/{promotionId}")
    public PromotionResponse updatePromotion(
            @PathVariable Long promotionId,
            @Valid @RequestBody AdminPromotionRequest request
    ) {
        return promotionService.updatePromotion(promotionId, request);
    }

    @DeleteMapping("/{promotionId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void archivePromotion(@PathVariable Long promotionId) {
        promotionService.archivePromotion(promotionId);
    }

    @PostMapping("/{promotionId}/products")
    public PromotionProductResponse addPromotionProduct(
            @PathVariable Long promotionId,
            @Valid @RequestBody PromotionProductRequest request
    ) {
        return promotionService.addPromotionProduct(promotionId, request);
    }

    @DeleteMapping("/{promotionId}/products/{productId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void removePromotionProduct(
            @PathVariable Long promotionId,
            @PathVariable Long productId
    ) {
        promotionService.removePromotionProduct(promotionId, productId);
    }

    @PostMapping("/{promotionId}/categories")
    public PromotionCategoryResponse addPromotionCategory(
            @PathVariable Long promotionId,
            @Valid @RequestBody PromotionCategoryRequest request
    ) {
        return promotionService.addPromotionCategory(promotionId, request);
    }

    @DeleteMapping("/{promotionId}/categories/{categoryId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void removePromotionCategory(
            @PathVariable Long promotionId,
            @PathVariable Long categoryId
    ) {
        promotionService.removePromotionCategory(promotionId, categoryId);
    }

    @DeleteMapping("/{promotionId}/targets")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void clearPromotionTargets(@PathVariable Long promotionId) {
        promotionService.clearPromotionTargets(promotionId);
    }

    @GetMapping("/{promotionId}/products")
    public List<PromotionProductResponse> listPromotionProducts(@PathVariable Long promotionId) {
        return promotionService.listPromotionProducts(promotionId);
    }

    @GetMapping("/{promotionId}/categories")
    public List<PromotionCategoryResponse> listPromotionCategories(@PathVariable Long promotionId) {
        return promotionService.listPromotionCategories(promotionId);
    }
}
