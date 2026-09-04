package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.PromotionProduct;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PromotionProductRepository extends JpaRepository<PromotionProduct, Long> {
    boolean existsByPromotion_IdAndProduct_Id(Long promotionId, Long productId);

    Optional<PromotionProduct> findByPromotion_IdAndProduct_Id(Long promotionId, Long productId);

    List<PromotionProduct> findByPromotion_IdOrderByCreatedAtDescIdDesc(Long promotionId);

    List<PromotionProduct> findByPromotion_IdInAndActive(Collection<Long> promotionIds, Boolean active);

    List<PromotionProduct> findByProduct_IdAndActiveOrderByCreatedAtDescIdDesc(Long productId, Boolean active);

    void deleteByPromotion_Id(Long promotionId);
}
