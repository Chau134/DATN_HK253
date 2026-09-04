package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Payment;
import com.example.serviceapiecommerce.entity.PaymentStatus;
import jakarta.persistence.LockModeType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PaymentRepository extends JpaRepository<Payment, Long> {
    Optional<Payment> findByPaymentNumber(String paymentNumber);

    boolean existsByPaymentNumber(String paymentNumber);

    Optional<Payment> findByIdempotencyKey(String idempotencyKey);

    Optional<Payment> findByProviderAndGatewayPaymentId(String provider, String gatewayPaymentId);

    Optional<Payment> findByIdAndUserAccount_Id(Long paymentId, Long userAccountId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select payment
            from Payment payment
            join fetch payment.order customerOrder
            join fetch payment.userAccount userAccount
            where payment.id = :paymentId
            """)
    Optional<Payment> findByIdForUpdate(@Param("paymentId") Long paymentId);

    List<Payment> findByOrder_IdOrderByCreatedAtDescIdDesc(Long orderId);

    @Query("""
            select payment
            from Payment payment
            join fetch payment.order customerOrder
            where customerOrder.id in :orderIds
            order by customerOrder.id, payment.createdAt desc, payment.id desc
            """)
    List<Payment> findByOrderIdsOrderByLatest(@Param("orderIds") Collection<Long> orderIds);

    @Query("""
            select payment
            from Payment payment
            join fetch payment.order customerOrder
            where payment.userAccount.id = :userAccountId
            order by payment.createdAt desc, payment.id desc
            """)
    List<Payment> findByUserAccountIdWithOrderOrderByLatest(@Param("userAccountId") Long userAccountId);

    List<Payment> findByUserAccount_IdAndStatusOrderByCreatedAtDescIdDesc(Long userAccountId, PaymentStatus status);

    List<Payment> findByStatusOrderByCreatedAtDescIdDesc(PaymentStatus status);
}
