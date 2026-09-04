package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Promotion;
import com.example.serviceapiecommerce.entity.PromotionStatus;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PromotionRepository extends JpaRepository<Promotion, Long> {
    List<Promotion> findByStatusOrderByPriorityDescCreatedAtDescIdDesc(PromotionStatus status);

    List<Promotion> findByEligibleUserAccount_IdOrderByPriorityDescCreatedAtDescIdDesc(Long userAccountId);
}
