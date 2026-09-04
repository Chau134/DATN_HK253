package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.PaymentWebhookEvent;
import com.example.serviceapiecommerce.entity.PaymentWebhookEventStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaymentWebhookEventRepository extends JpaRepository<PaymentWebhookEvent, Long> {
    Optional<PaymentWebhookEvent> findByProviderAndEventId(String provider, String eventId);

    boolean existsByProviderAndEventId(String provider, String eventId);

    List<PaymentWebhookEvent> findByPayment_IdOrderByReceivedAtDescIdDesc(Long paymentId);

    List<PaymentWebhookEvent> findByPaymentTransaction_IdOrderByReceivedAtDescIdDesc(Long paymentTransactionId);

    List<PaymentWebhookEvent> findByProcessingStatusOrderByReceivedAtAscIdAsc(PaymentWebhookEventStatus processingStatus);

    List<PaymentWebhookEvent> findByProviderOrderByReceivedAtDescIdDesc(String provider);
}
