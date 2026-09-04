package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.CouponRedemption;
import com.example.serviceapiecommerce.entity.CouponRedemptionStatus;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CouponRedemptionRepository extends JpaRepository<CouponRedemption, Long> {
    Optional<CouponRedemption> findByRedemptionKey(String redemptionKey);

    Optional<CouponRedemption> findByCoupon_IdAndOrder_Id(Long couponId, Long orderId);

    boolean existsByCoupon_IdAndOrder_Id(Long couponId, Long orderId);

    long countByCoupon_IdAndStatus(Long couponId, CouponRedemptionStatus status);

    long countByCoupon_IdAndStatusIn(Long couponId, Collection<CouponRedemptionStatus> statuses);

    long countByCoupon_IdAndUserAccount_IdAndStatus(
            Long couponId,
            Long userAccountId,
            CouponRedemptionStatus status
    );

    long countByCoupon_IdAndUserAccount_IdAndStatusIn(
            Long couponId,
            Long userAccountId,
            Collection<CouponRedemptionStatus> statuses
    );

    @Query("""
            select redemption.coupon.id as couponId, count(redemption.id) as redemptionCount
            from CouponRedemption redemption
            where redemption.coupon.id in :couponIds
              and redemption.userAccount.id = :userAccountId
              and redemption.status in :statuses
            group by redemption.coupon.id
            """)
    List<CouponUsageCount> countUsageByCouponIdsAndUser(
            @Param("couponIds") Collection<Long> couponIds,
            @Param("userAccountId") Long userAccountId,
            @Param("statuses") Collection<CouponRedemptionStatus> statuses
    );

    List<CouponRedemption> findByCoupon_IdOrderByCreatedAtDescIdDesc(Long couponId);

    List<CouponRedemption> findByUserAccount_IdOrderByCreatedAtDescIdDesc(Long userAccountId);

    List<CouponRedemption> findByOrder_IdOrderByCreatedAtDescIdDesc(Long orderId);

    List<CouponRedemption> findByOrder_IdAndStatusInOrderByCreatedAtDescIdDesc(
            Long orderId,
            Collection<CouponRedemptionStatus> statuses
    );

    interface CouponUsageCount {
        Long getCouponId();

        long getRedemptionCount();
    }
}
