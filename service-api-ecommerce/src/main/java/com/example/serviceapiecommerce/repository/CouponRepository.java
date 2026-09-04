package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Coupon;
import com.example.serviceapiecommerce.entity.CouponStatus;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CouponRepository extends JpaRepository<Coupon, Long> {
    Optional<Coupon> findByCode(String code);

    Optional<Coupon> findByCodeIgnoreCase(String code);

    boolean existsByCode(String code);

    boolean existsByCodeIgnoreCase(String code);

    @EntityGraph(attributePaths = "eligibleUserAccount")
    List<Coupon> findByStatusOrderByCreatedAtDescIdDesc(CouponStatus status);

    @EntityGraph(attributePaths = "eligibleUserAccount")
    List<Coupon> findAllByOrderByCreatedAtDescIdDesc();

    List<Coupon> findByEligibleUserAccount_IdOrderByCreatedAtDescIdDesc(Long userAccountId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select coupon
            from Coupon coupon
            left join fetch coupon.eligibleUserAccount eligibleUserAccount
            where lower(coupon.code) = lower(:code)
            """)
    Optional<Coupon> findByCodeIgnoreCaseForUpdate(@Param("code") String code);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select coupon
            from Coupon coupon
            left join fetch coupon.eligibleUserAccount eligibleUserAccount
            where coupon.id = :couponId
            """)
    Optional<Coupon> findByIdForUpdate(@Param("couponId") Long couponId);
}
