package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.payment.PaymentResponse;
import com.example.serviceapiecommerce.dto.payment.PaymentTransactionResponse;
import com.example.serviceapiecommerce.entity.Payment;
import com.example.serviceapiecommerce.entity.PaymentTransaction;
import com.example.serviceapiecommerce.repository.PaymentTransactionRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class PaymentResponseMapper {
    private final PaymentTransactionRepository paymentTransactionRepository;

    public PaymentResponseMapper(PaymentTransactionRepository paymentTransactionRepository) {
        this.paymentTransactionRepository = paymentTransactionRepository;
    }

    public PaymentResponse toResponse(Payment payment) {
        return toResponse(
                payment,
                paymentTransactionRepository.findByPayment_IdOrderByCreatedAtDescIdDesc(payment.getId())
        );
    }

    public List<PaymentResponse> toResponses(List<Payment> payments) {
        if (payments.isEmpty()) {
            return List.of();
        }
        List<Long> paymentIds = payments.stream().map(Payment::getId).toList();
        Map<Long, List<PaymentTransaction>> transactionsByPaymentId = new LinkedHashMap<>();
        for (PaymentTransaction transaction : paymentTransactionRepository.findByPaymentIdsOrderByLatest(paymentIds)) {
            transactionsByPaymentId
                    .computeIfAbsent(transaction.getPayment().getId(), ignored -> new ArrayList<>())
                    .add(transaction);
        }
        return payments.stream()
                .map(payment -> toResponse(
                        payment,
                        transactionsByPaymentId.getOrDefault(payment.getId(), List.of())
                ))
                .toList();
    }

    private PaymentResponse toResponse(Payment payment, List<PaymentTransaction> paymentTransactions) {
        List<PaymentTransactionResponse> transactions = paymentTransactions
                .stream()
                .map(PaymentResponseMapper::toTransaction)
                .toList();
        return new PaymentResponse(
                payment.getId(),
                payment.getPaymentNumber(),
                payment.getOrder().getId(),
                payment.getOrder().getOrderNumber(),
                payment.getMethod(),
                payment.getStatus(),
                payment.getAmount(),
                payment.getRefundedAmount(),
                payment.getCurrency(),
                payment.getProvider(),
                payment.getGatewayPaymentId(),
                payment.getGatewayOrderId(),
                payment.getIdempotencyKey(),
                payment.getRequestedAt(),
                payment.getPaidAt(),
                payment.getFailedAt(),
                payment.getCancelledAt(),
                payment.getRefundedAt(),
                payment.getFailureCode(),
                payment.getFailureMessage(),
                transactions,
                payment.getCreatedAt(),
                payment.getUpdatedAt()
        );
    }

    private static PaymentTransactionResponse toTransaction(PaymentTransaction transaction) {
        return new PaymentTransactionResponse(
                transaction.getId(),
                transaction.getTransactionType(),
                transaction.getStatus(),
                transaction.getAmount(),
                transaction.getCurrency(),
                transaction.getProvider(),
                transaction.getGatewayTransactionId(),
                transaction.getGatewayPaymentId(),
                transaction.getIdempotencyKey(),
                transaction.getFailureCode(),
                transaction.getFailureMessage(),
                transaction.getProcessedAt(),
                transaction.getCreatedAt()
        );
    }
}
