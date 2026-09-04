package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.PromotionCategory;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PromotionCategoryRepository extends JpaRepository<PromotionCategory, Long> {
    boolean existsByPromotion_IdAndCategory_Id(Long promotionId, Long categoryId);

    Optional<PromotionCategory> findByPromotion_IdAndCategory_Id(Long promotionId, Long categoryId);

    List<PromotionCategory> findByPromotion_IdOrderByCreatedAtDescIdDesc(Long promotionId);

    List<PromotionCategory> findByPromotion_IdInAndActive(Collection<Long> promotionIds, Boolean active);

    List<PromotionCategory> findByCategory_IdAndActiveOrderByCreatedAtDescIdDesc(Long categoryId, Boolean active);

    void deleteByPromotion_Id(Long promotionId);
}
