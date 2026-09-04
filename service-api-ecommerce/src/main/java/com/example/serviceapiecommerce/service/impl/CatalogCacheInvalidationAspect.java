package com.example.serviceapiecommerce.service.impl;

import org.aspectj.lang.annotation.AfterReturning;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

@Aspect
@Component
public class CatalogCacheInvalidationAspect {
    private final CatalogQueryCache cache;

    public CatalogCacheInvalidationAspect(CatalogQueryCache cache) {
        this.cache = cache;
    }

    @AfterReturning("""
            execution(* com.example.serviceapiecommerce.repository.ProductRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductRepository.delete*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductImageRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductImageRepository.delete*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductCategoryRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductCategoryRepository.delete*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductVariantRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductVariantRepository.delete*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductPriceRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductPriceRepository.delete*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductReviewSummaryRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.ProductReviewSummaryRepository.delete*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.PromotionRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.PromotionRepository.delete*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.PromotionProductRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.PromotionProductRepository.delete*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.PromotionCategoryRepository.save*(..)) ||
            execution(* com.example.serviceapiecommerce.repository.PromotionCategoryRepository.delete*(..))
            """)
    public void invalidateCatalogPages() {
        cache.invalidateAll();
    }
}
