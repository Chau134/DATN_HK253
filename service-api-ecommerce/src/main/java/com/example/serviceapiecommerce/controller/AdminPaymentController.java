package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.payment.PaymentActionRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentRefundRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.PaymentService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/payments")
public class AdminPaymentController {
    private static final Logger log = LoggerFactory.getLogger(AdminPaymentController.class);

    private final PaymentService paymentService;

    public AdminPaymentController(PaymentService paymentService) {
        this.paymentService = paymentService;
    }

    @PostMapping("/{paymentId}/cod/confirm")
    public PaymentResponse confirmCodPayment(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long paymentId,
            @Valid @RequestBody(required = false) PaymentActionRequest request
    ) {
        PaymentResponse response = paymentService.confirmCodPayment(currentUser.id(), paymentId, request);
        log.info(
                "admin_payment_cod_confirm_success admin_user_id={} payment_id={} order_id={} status={}",
                currentUser.id(),
                response.id(),
                response.orderId(),
                response.status()
        );
        return response;
    }

    @PostMapping("/{paymentId}/fail")
    public PaymentResponse failPayment(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long paymentId,
            @Valid @RequestBody(required = false) PaymentActionRequest request
    ) {
        PaymentResponse response = paymentService.failPayment(currentUser.id(), paymentId, request);
        log.info(
                "admin_payment_fail_success admin_user_id={} payment_id={} order_id={} status={}",
                currentUser.id(),
                response.id(),
                response.orderId(),
                response.status()
        );
        return response;
    }

    @PostMapping("/{paymentId}/refund")
    public PaymentResponse refundPayment(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long paymentId,
            @Valid @RequestBody(required = false) PaymentRefundRequest request
    ) {
        PaymentResponse response = paymentService.refundPayment(currentUser.id(), paymentId, request);
        log.info(
                "admin_payment_refund_success admin_user_id={} payment_id={} order_id={} status={}",
                currentUser.id(),
                response.id(),
                response.orderId(),
                response.status()
        );
        return response;
    }
}
