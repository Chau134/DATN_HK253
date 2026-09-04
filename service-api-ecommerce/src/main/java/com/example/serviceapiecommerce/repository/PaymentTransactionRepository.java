package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.PaymentTransaction;
import com.example.serviceapiecommerce.entity.PaymentTransactionStatus;
import com.example.serviceapiecommerce.entity.PaymentTransactionType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PaymentTransactionRepository extends JpaRepository<PaymentTransaction, Long> {
    Optional<PaymentTransaction> findByIdempotencyKey(String idempotencyKey);

    Optional<PaymentTransaction> findByProviderAndGatewayTransactionId(String provider, String gatewayTransactionId);

    List<PaymentTransaction> findByPayment_IdOrderByCreatedAtDescIdDesc(Long paymentId);

    @Query("""
            select paymentTransaction
            from PaymentTransaction paymentTransaction
            join fetch paymentTransaction.payment payment
            where payment.id in :paymentIds
            order by payment.id, paymentTransaction.createdAt desc, paymentTransaction.id desc
            """)
    List<PaymentTransaction> findByPaymentIdsOrderByLatest(@Param("paymentIds") Collection<Long> paymentIds);

    List<PaymentTransaction> findByOrder_IdOrderByCreatedAtDescIdDesc(Long orderId);

    List<PaymentTransaction> findByTransactionTypeOrderByCreatedAtDescIdDesc(PaymentTransactionType transactionType);

    List<PaymentTransaction> findByStatusOrderByCreatedAtDescIdDesc(PaymentTransactionStatus status);
}
