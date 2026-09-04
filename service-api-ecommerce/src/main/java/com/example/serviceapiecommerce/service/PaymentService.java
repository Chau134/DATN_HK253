package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.payment.CreateCodPaymentRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentActionRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentRefundRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentResponse;
import com.example.serviceapiecommerce.dto.payment.PaymentWebhookIngestResponse;
import java.util.List;
import java.util.Map;

public interface PaymentService {
    PaymentResponse createCodPayment(Long userAccountId, CreateCodPaymentRequest request);

    List<PaymentResponse> listPayments(Long userAccountId);

    PaymentResponse getPayment(Long userAccountId, Long paymentId);

    PaymentResponse cancelPayment(Long userAccountId, Long paymentId, PaymentActionRequest request);

    PaymentResponse confirmCodPayment(Long adminUserAccountId, Long paymentId, PaymentActionRequest request);

    PaymentResponse failPayment(Long adminUserAccountId, Long paymentId, PaymentActionRequest request);

    PaymentResponse refundPayment(Long adminUserAccountId, Long paymentId, PaymentRefundRequest request);

    PaymentWebhookIngestResponse ingestWebhook(
            String provider,
            String eventId,
            String eventType,
            String gatewayPaymentId,
            String gatewayTransactionId,
            String signature,
            Map<String, String> headers,
            String payload
    );
}
