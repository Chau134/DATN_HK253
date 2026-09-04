package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.promotion.AdminPromotionRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionCategoryRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionCategoryResponse;
import com.example.serviceapiecommerce.dto.promotion.PromotionProductRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionProductResponse;
import com.example.serviceapiecommerce.dto.promotion.PromotionResponse;
import com.example.serviceapiecommerce.entity.OrderItem;
import com.example.serviceapiecommerce.entity.PromotionStatus;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public interface PromotionService {
    PromotionResponse createPromotion(AdminPromotionRequest request);

    PromotionResponse updatePromotion(Long promotionId, AdminPromotionRequest request);

    List<PromotionResponse> listPromotions(PromotionStatus status);

    PromotionResponse getPromotion(Long promotionId);

    void archivePromotion(Long promotionId);

    PromotionProductResponse addPromotionProduct(Long promotionId, PromotionProductRequest request);

    void removePromotionProduct(Long promotionId, Long productId);

    PromotionCategoryResponse addPromotionCategory(Long promotionId, PromotionCategoryRequest request);

    void removePromotionCategory(Long promotionId, Long categoryId);

    List<PromotionProductResponse> listPromotionProducts(Long promotionId);

    List<PromotionCategoryResponse> listPromotionCategories(Long promotionId);

    void clearPromotionTargets(Long promotionId);

    BigDecimal applyAutomaticPromotions(
            Long userAccountId,
            List<OrderItem> orderItems,
            BigDecimal subtotal,
            String currency,
            Instant now
    );
}
