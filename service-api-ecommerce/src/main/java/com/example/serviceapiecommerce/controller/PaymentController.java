package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.payment.CreateCodPaymentRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentActionRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentResponse;
import com.example.serviceapiecommerce.dto.payment.PaymentWebhookIngestResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.PaymentService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/payments")
public class PaymentController {
    private static final Logger log = LoggerFactory.getLogger(PaymentController.class);

    private final PaymentService paymentService;

    public PaymentController(PaymentService paymentService) {
        this.paymentService = paymentService;
    }

    @PostMapping("/cod")
    public PaymentResponse createCodPayment(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody CreateCodPaymentRequest request
    ) {
        PaymentResponse response = paymentService.createCodPayment(currentUser.id(), request);
        log.info(
                "payment_cod_create_success user_id={} order_id={} payment_id={} status={}",
                currentUser.id(),
                response.orderId(),
                response.id(),
                response.status()
        );
        return response;
    }

    @GetMapping
    public List<PaymentResponse> payments(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return paymentService.listPayments(currentUser.id());
    }

    @GetMapping("/{paymentId}")
    public PaymentResponse payment(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long paymentId
    ) {
        return paymentService.getPayment(currentUser.id(), paymentId);
    }

    @PostMapping("/{paymentId}/cancel")
    public PaymentResponse cancelPayment(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long paymentId,
            @Valid @RequestBody(required = false) PaymentActionRequest request
    ) {
        PaymentResponse response = paymentService.cancelPayment(currentUser.id(), paymentId, request);
        log.info(
                "payment_cancel_success user_id={} payment_id={} status={}",
                currentUser.id(),
                response.id(),
                response.status()
        );
        return response;
    }

    @PostMapping("/webhooks/{provider}")
    public PaymentWebhookIngestResponse ingestWebhook(
            @PathVariable String provider,
            @RequestHeader Map<String, String> headers,
            @RequestBody(required = false) String payload
    ) {
        PaymentWebhookIngestResponse response = paymentService.ingestWebhook(
                provider,
                firstHeader(headers, "x-event-id", "x-webhook-event-id", "x-gateway-event-id"),
                firstHeader(headers, "x-event-type", "x-webhook-event-type"),
                firstHeader(headers, "x-gateway-payment-id", "x-payment-id"),
                firstHeader(headers, "x-gateway-transaction-id", "x-transaction-id"),
                firstHeader(headers, "x-signature", "x-webhook-signature"),
                headers,
                payload
        );
        log.info(
                "payment_webhook_ingest provider={} event_id={} duplicate={} status={}",
                provider,
                response.eventId(),
                response.duplicate(),
                response.processingStatus()
        );
        return response;
    }

    private static String firstHeader(Map<String, String> headers, String... names) {
        for (String name : names) {
            for (Map.Entry<String, String> header : headers.entrySet()) {
                if (header.getKey().equalsIgnoreCase(name)
                        && header.getValue() != null
                        && !header.getValue().isBlank()) {
                    return header.getValue().trim();
                }
            }
        }
        return null;
    }
}
