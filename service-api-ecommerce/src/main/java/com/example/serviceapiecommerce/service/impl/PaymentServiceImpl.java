package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.payment.CreateCodPaymentRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentActionRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentRefundRequest;
import com.example.serviceapiecommerce.dto.payment.PaymentResponse;
import com.example.serviceapiecommerce.dto.payment.PaymentWebhookIngestResponse;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.entity.OrderStatusHistory;
import com.example.serviceapiecommerce.entity.Payment;
import com.example.serviceapiecommerce.entity.PaymentMethod;
import com.example.serviceapiecommerce.entity.PaymentStatus;
import com.example.serviceapiecommerce.entity.PaymentTransaction;
import com.example.serviceapiecommerce.entity.PaymentTransactionStatus;
import com.example.serviceapiecommerce.entity.PaymentTransactionType;
import com.example.serviceapiecommerce.entity.PaymentWebhookEvent;
import com.example.serviceapiecommerce.entity.PaymentWebhookEventStatus;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.repository.OrderRepository;
import com.example.serviceapiecommerce.repository.OrderStatusHistoryRepository;
import com.example.serviceapiecommerce.repository.PaymentRepository;
import com.example.serviceapiecommerce.repository.PaymentTransactionRepository;
import com.example.serviceapiecommerce.repository.PaymentWebhookEventRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.CouponService;
import com.example.serviceapiecommerce.service.InventoryService;
import com.example.serviceapiecommerce.service.PaymentService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class PaymentServiceImpl implements PaymentService {
    private static final String DEFAULT_CURRENCY = "VND";
    private static final String PROVIDER_COD = "COD";
    private static final BigDecimal ZERO = BigDecimal.ZERO;
    private static final EnumSet<PaymentStatus> ACTIVE_PAYMENT_STATUSES =
            EnumSet.of(PaymentStatus.PENDING, PaymentStatus.AUTHORIZED, PaymentStatus.PAID);
    private static final EnumSet<OrderStatus> PAYABLE_ORDER_STATUSES =
            EnumSet.of(OrderStatus.PENDING, OrderStatus.CONFIRMED);

    private final PaymentRepository paymentRepository;
    private final PaymentTransactionRepository paymentTransactionRepository;
    private final PaymentWebhookEventRepository paymentWebhookEventRepository;
    private final OrderRepository orderRepository;
    private final OrderStatusHistoryRepository orderStatusHistoryRepository;
    private final UserAccountRepository userAccountRepository;
    private final InventoryService inventoryService;
    private final CouponService couponService;
    private final PaymentNumberGenerator paymentNumberGenerator;
    private final PaymentResponseMapper paymentResponseMapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public PaymentServiceImpl(
            PaymentRepository paymentRepository,
            PaymentTransactionRepository paymentTransactionRepository,
            PaymentWebhookEventRepository paymentWebhookEventRepository,
            OrderRepository orderRepository,
            OrderStatusHistoryRepository orderStatusHistoryRepository,
            UserAccountRepository userAccountRepository,
            InventoryService inventoryService,
            CouponService couponService,
            PaymentNumberGenerator paymentNumberGenerator,
            PaymentResponseMapper paymentResponseMapper
    ) {
        this.paymentRepository = paymentRepository;
        this.paymentTransactionRepository = paymentTransactionRepository;
        this.paymentWebhookEventRepository = paymentWebhookEventRepository;
        this.orderRepository = orderRepository;
        this.orderStatusHistoryRepository = orderStatusHistoryRepository;
        this.userAccountRepository = userAccountRepository;
        this.inventoryService = inventoryService;
        this.couponService = couponService;
        this.paymentNumberGenerator = paymentNumberGenerator;
        this.paymentResponseMapper = paymentResponseMapper;
    }

    @Override
    @Transactional
    public PaymentResponse createCodPayment(Long userAccountId, CreateCodPaymentRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "payment_request_required");
        }
        String idempotencyKey = blankToNull(request.idempotencyKey());
        if (idempotencyKey != null) {
            Optional<Payment> existing = paymentRepository.findByIdempotencyKey(idempotencyKey);
            if (existing.isPresent()) {
                assertOwned(existing.get(), userAccountId);
                return paymentResponseMapper.toResponse(existing.get());
            }
        }

        Order order = orderRepository.findByIdAndUserAccountIdForUpdate(request.orderId(), userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order_not_found"));
        if (!PAYABLE_ORDER_STATUSES.contains(order.getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_not_payable");
        }

        Optional<Payment> activePayment = paymentRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(order.getId())
                .stream()
                .filter(payment -> payment.getMethod() == PaymentMethod.COD)
                .filter(payment -> ACTIVE_PAYMENT_STATUSES.contains(payment.getStatus()))
                .findFirst();
        if (activePayment.isPresent()) {
            return paymentResponseMapper.toResponse(activePayment.get());
        }

        Instant now = Instant.now();
        Payment payment = new Payment();
        payment.setPaymentNumber(paymentNumberGenerator.nextPaymentNumber());
        payment.setOrder(order);
        payment.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
        payment.setMethod(PaymentMethod.COD);
        payment.setStatus(PaymentStatus.PENDING);
        payment.setAmount(nonNullAmount(order.getTotalAmount()));
        payment.setRefundedAmount(ZERO);
        payment.setCurrency(blankToDefault(order.getCurrency(), DEFAULT_CURRENCY));
        payment.setProvider(PROVIDER_COD);
        payment.setIdempotencyKey(idempotencyKey);
        payment.setRequestedAt(now);
        payment.setMetadata(blankToNull(request.note()));
        payment.setCreatedAt(now);
        payment.setUpdatedAt(now);
        Payment savedPayment = paymentRepository.save(payment);

        transitionOrder(
                order,
                OrderStatus.CONFIRMED,
                userAccountId,
                "cod_payment_created",
                blankToNull(request.note()),
                now
        );
        return paymentResponseMapper.toResponse(savedPayment);
    }

    @Override
    @Transactional(readOnly = true)
    public List<PaymentResponse> listPayments(Long userAccountId) {
        return paymentResponseMapper.toResponses(
                paymentRepository.findByUserAccountIdWithOrderOrderByLatest(userAccountId)
        );
    }

    @Override
    @Transactional(readOnly = true)
    public PaymentResponse getPayment(Long userAccountId, Long paymentId) {
        Payment payment = paymentRepository.findByIdAndUserAccount_Id(paymentId, userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "payment_not_found"));
        return paymentResponseMapper.toResponse(payment);
    }

    @Override
    @Transactional
    public PaymentResponse cancelPayment(Long userAccountId, Long paymentId, PaymentActionRequest request) {
        Payment payment = paymentRepository.findByIdForUpdate(paymentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "payment_not_found"));
        assertOwned(payment, userAccountId);
        if (payment.getStatus() == PaymentStatus.CANCELLED) {
            return paymentResponseMapper.toResponse(payment);
        }
        if (payment.getStatus() == PaymentStatus.PAID
                || payment.getStatus() == PaymentStatus.REFUNDED
                || payment.getStatus() == PaymentStatus.PARTIALLY_REFUNDED) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "payment_cannot_be_cancelled");
        }

        String idempotencyKey = actionIdempotencyKey(request, "cancel-payment:payment:" + payment.getId());
        Optional<PaymentTransaction> existingTransaction = paymentTransactionRepository.findByIdempotencyKey(idempotencyKey);
        if (existingTransaction.isPresent()) {
            return paymentResponseMapper.toResponse(existingTransaction.get().getPayment());
        }

        Instant now = Instant.now();
        String reason = actionReason(request, "customer_payment_cancelled");
        payment.setStatus(PaymentStatus.CANCELLED);
        payment.setCancelledAt(now);
        payment.setUpdatedAt(now);
        paymentRepository.save(payment);
        saveTransaction(
                payment,
                PaymentTransactionType.CANCEL,
                PaymentTransactionStatus.SUCCESS,
                payment.getAmount(),
                idempotencyKey,
                null,
                null,
                reason,
                now
        );
        cancelOrderForPayment(payment.getOrder(), userAccountId, reason, actionNote(request), now);
        return paymentResponseMapper.toResponse(payment);
    }

    @Override
    @Transactional
    public PaymentResponse confirmCodPayment(Long adminUserAccountId, Long paymentId, PaymentActionRequest request) {
        Payment payment = lockedPayment(paymentId);
        if (payment.getMethod() != PaymentMethod.COD) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "payment_method_not_cod");
        }
        if (payment.getStatus() == PaymentStatus.AUTHORIZED || payment.getStatus() == PaymentStatus.PAID) {
            return paymentResponseMapper.toResponse(payment);
        }
        if (payment.getStatus() != PaymentStatus.PENDING) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "payment_cannot_be_confirmed");
        }

        String idempotencyKey = actionIdempotencyKey(request, "cod-confirm:payment:" + payment.getId());
        Optional<PaymentTransaction> existingTransaction = paymentTransactionRepository.findByIdempotencyKey(idempotencyKey);
        if (existingTransaction.isPresent()) {
            return paymentResponseMapper.toResponse(existingTransaction.get().getPayment());
        }

        Instant now = Instant.now();
        String reason = actionReason(request, "cod_payment_confirmed");
        inventoryService.commitSale(payment.getOrder().getId(), adminUserAccountId, reason);

        payment.setStatus(PaymentStatus.AUTHORIZED);
        payment.setAuthorizedAt(now);
        payment.setUpdatedAt(now);
        paymentRepository.save(payment);
        saveTransaction(
                payment,
                PaymentTransactionType.COD_CONFIRM,
                PaymentTransactionStatus.SUCCESS,
                payment.getAmount(),
                idempotencyKey,
                null,
                null,
                reason,
                now
        );
        transitionOrder(payment.getOrder(), OrderStatus.SHIPPING, adminUserAccountId, reason, actionNote(request), now);
        return paymentResponseMapper.toResponse(payment);
    }

    @Override
    @Transactional
    public PaymentResponse failPayment(Long adminUserAccountId, Long paymentId, PaymentActionRequest request) {
        Payment payment = lockedPayment(paymentId);
        if (payment.getStatus() == PaymentStatus.FAILED) {
            return paymentResponseMapper.toResponse(payment);
        }
        if (payment.getStatus() == PaymentStatus.PAID
                || payment.getStatus() == PaymentStatus.REFUNDED
                || payment.getStatus() == PaymentStatus.PARTIALLY_REFUNDED) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "payment_cannot_be_failed");
        }

        String idempotencyKey = actionIdempotencyKey(request, "fail-payment:payment:" + payment.getId());
        Optional<PaymentTransaction> existingTransaction = paymentTransactionRepository.findByIdempotencyKey(idempotencyKey);
        if (existingTransaction.isPresent()) {
            return paymentResponseMapper.toResponse(existingTransaction.get().getPayment());
        }

        Instant now = Instant.now();
        String reason = actionReason(request, "payment_failed");
        payment.setStatus(PaymentStatus.FAILED);
        payment.setFailedAt(now);
        payment.setFailureCode(blankToNull(request == null ? null : request.failureCode()));
        payment.setFailureMessage(blankToNull(request == null ? null : request.failureMessage()));
        payment.setUpdatedAt(now);
        paymentRepository.save(payment);
        saveTransaction(
                payment,
                PaymentTransactionType.SALE,
                PaymentTransactionStatus.FAILED,
                payment.getAmount(),
                idempotencyKey,
                payment.getFailureCode(),
                payment.getFailureMessage(),
                reason,
                now
        );
        cancelOrderForPayment(payment.getOrder(), adminUserAccountId, reason, actionNote(request), now);
        return paymentResponseMapper.toResponse(payment);
    }

    @Override
    @Transactional
    public PaymentResponse refundPayment(Long adminUserAccountId, Long paymentId, PaymentRefundRequest request) {
        Payment payment = lockedPayment(paymentId);
        if (payment.getStatus() != PaymentStatus.PAID && payment.getStatus() != PaymentStatus.PARTIALLY_REFUNDED) {
            if (payment.getStatus() == PaymentStatus.REFUNDED) {
                return paymentResponseMapper.toResponse(payment);
            }
            throw new ResponseStatusException(HttpStatus.CONFLICT, "payment_cannot_be_refunded");
        }

        String idempotencyKey = refundIdempotencyKey(request, "refund-payment:payment:" + payment.getId());
        Optional<PaymentTransaction> existingTransaction = paymentTransactionRepository.findByIdempotencyKey(idempotencyKey);
        if (existingTransaction.isPresent()) {
            return paymentResponseMapper.toResponse(existingTransaction.get().getPayment());
        }

        BigDecimal remaining = payment.getAmount().subtract(nonNullAmount(payment.getRefundedAmount()));
        BigDecimal refundAmount = request == null || request.amount() == null ? remaining : request.amount();
        if (refundAmount.compareTo(ZERO) <= 0 || refundAmount.compareTo(remaining) > 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "invalid_refund_amount");
        }

        Instant now = Instant.now();
        String reason = blankToDefault(request == null ? null : request.reason(), "payment_refunded");
        BigDecimal refundedAmount = nonNullAmount(payment.getRefundedAmount()).add(refundAmount);
        payment.setRefundedAmount(refundedAmount);
        payment.setRefundedAt(now);
        payment.setStatus(refundedAmount.compareTo(payment.getAmount()) >= 0
                ? PaymentStatus.REFUNDED
                : PaymentStatus.PARTIALLY_REFUNDED);
        payment.setUpdatedAt(now);
        paymentRepository.save(payment);
        saveTransaction(
                payment,
                PaymentTransactionType.REFUND,
                PaymentTransactionStatus.SUCCESS,
                refundAmount,
                idempotencyKey,
                null,
                null,
                reason,
                now
        );

        if (payment.getStatus() == PaymentStatus.REFUNDED) {
            inventoryService.releaseOrCancelOrderStock(payment.getOrder().getId(), adminUserAccountId, reason);
            couponService.refundOrderRedemptions(payment.getOrder().getId(), reason, now);
            transitionOrder(payment.getOrder(), OrderStatus.REFUNDED, adminUserAccountId, reason, refundNote(request), now);
        }
        return paymentResponseMapper.toResponse(payment);
    }

    @Override
    @Transactional
    public PaymentWebhookIngestResponse ingestWebhook(
            String provider,
            String eventId,
            String eventType,
            String gatewayPaymentId,
            String gatewayTransactionId,
            String signature,
            Map<String, String> headers,
            String payload
    ) {
        String normalizedProvider = requiredText(provider, "provider_required");
        String normalizedEventId = requiredText(eventId, "event_id_required");
        Optional<PaymentWebhookEvent> existing = paymentWebhookEventRepository.findByProviderAndEventId(
                normalizedProvider,
                normalizedEventId
        );
        if (existing.isPresent()) {
            return toWebhookResponse(existing.get(), true);
        }

        Instant now = Instant.now();
        PaymentWebhookEvent event = new PaymentWebhookEvent();
        event.setProvider(normalizedProvider);
        event.setEventId(normalizedEventId);
        event.setEventType(blankToNull(eventType));
        event.setGatewayPaymentId(blankToNull(gatewayPaymentId));
        event.setGatewayTransactionId(blankToNull(gatewayTransactionId));
        event.setSignature(blankToNull(signature));
        event.setHeaders(toJson(headers == null ? Map.of() : headers));
        event.setPayload(payload == null ? "" : payload);
        event.setProcessingStatus(PaymentWebhookEventStatus.RECEIVED);
        event.setReceivedAt(now);
        event.setCreatedAt(now);
        event.setUpdatedAt(now);

        if (event.getGatewayPaymentId() != null) {
            paymentRepository.findByProviderAndGatewayPaymentId(normalizedProvider, event.getGatewayPaymentId())
                    .ifPresent(event::setPayment);
        }
        if (event.getGatewayTransactionId() != null) {
            paymentTransactionRepository
                    .findByProviderAndGatewayTransactionId(normalizedProvider, event.getGatewayTransactionId())
                    .ifPresent(event::setPaymentTransaction);
        }

        return toWebhookResponse(paymentWebhookEventRepository.save(event), false);
    }

    private Payment lockedPayment(Long paymentId) {
        if (paymentId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "payment_id_required");
        }
        return paymentRepository.findByIdForUpdate(paymentId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "payment_not_found"));
    }

    private void cancelOrderForPayment(
            Order order,
            Long changedByUserAccountId,
            String reason,
            String note,
            Instant now
    ) {
        if (order.getStatus() == OrderStatus.CANCELLED || order.getStatus() == OrderStatus.REFUNDED) {
            return;
        }
        if (order.getStatus() == OrderStatus.PAID) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "paid_order_requires_refund");
        }
        inventoryService.releaseOrCancelOrderStock(order.getId(), changedByUserAccountId, reason);
        couponService.cancelOrderRedemptions(order.getId(), reason, now);
        transitionOrder(order, OrderStatus.CANCELLED, changedByUserAccountId, reason, note, now);
    }

    private void transitionOrder(
            Order order,
            OrderStatus toStatus,
            Long changedByUserAccountId,
            String reason,
            String note,
            Instant now
    ) {
        if (order.getStatus() == toStatus) {
            return;
        }
        OrderStatus previousStatus = order.getStatus();
        order.setStatus(toStatus);
        order.setUpdatedAt(now);
        if (toStatus == OrderStatus.CONFIRMED) {
            order.setConfirmedAt(now);
        } else if (toStatus == OrderStatus.PAID) {
            order.setPaidAt(now);
        } else if (toStatus == OrderStatus.CANCELLED) {
            order.setCancelledAt(now);
        }
        orderRepository.save(order);

        OrderStatusHistory history = new OrderStatusHistory();
        history.setOrder(order);
        history.setFromStatus(previousStatus);
        history.setToStatus(toStatus);
        history.setChangedByUserAccount(changedBy(changedByUserAccountId));
        history.setReason(reason);
        history.setNote(note);
        history.setCreatedAt(now);
        orderStatusHistoryRepository.save(history);
    }

    private PaymentTransaction saveTransaction(
            Payment payment,
            PaymentTransactionType transactionType,
            PaymentTransactionStatus status,
            BigDecimal amount,
            String idempotencyKey,
            String failureCode,
            String failureMessage,
            String reason,
            Instant now
    ) {
        PaymentTransaction transaction = new PaymentTransaction();
        transaction.setPayment(payment);
        transaction.setOrder(payment.getOrder());
        transaction.setTransactionType(transactionType);
        transaction.setStatus(status);
        transaction.setAmount(nonNullAmount(amount));
        transaction.setCurrency(blankToDefault(payment.getCurrency(), DEFAULT_CURRENCY));
        transaction.setProvider(payment.getProvider());
        transaction.setGatewayPaymentId(payment.getGatewayPaymentId());
        transaction.setIdempotencyKey(idempotencyKey);
        transaction.setFailureCode(failureCode);
        transaction.setFailureMessage(failureMessage);
        transaction.setRequestPayload(reason);
        transaction.setProcessedAt(now);
        transaction.setCreatedAt(now);
        return paymentTransactionRepository.save(transaction);
    }

    private void assertOwned(Payment payment, Long userAccountId) {
        if (!payment.getUserAccount().getId().equals(userAccountId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "payment_not_found");
        }
    }

    private UserAccount changedBy(Long userAccountId) {
        return userAccountId == null ? null : userAccountRepository.getReferenceById(userAccountId);
    }

    private String toJson(Map<String, String> headers) {
        try {
            return objectMapper.writeValueAsString(headers);
        } catch (JsonProcessingException exception) {
            return "{}";
        }
    }

    private static PaymentWebhookIngestResponse toWebhookResponse(PaymentWebhookEvent event, boolean duplicate) {
        return new PaymentWebhookIngestResponse(
                event.getId(),
                event.getProvider(),
                event.getEventId(),
                event.getEventType(),
                event.getProcessingStatus(),
                duplicate,
                event.getReceivedAt(),
                event.getProcessedAt()
        );
    }

    private static BigDecimal nonNullAmount(BigDecimal amount) {
        return amount == null ? ZERO : amount;
    }

    private static String actionIdempotencyKey(PaymentActionRequest request, String defaultValue) {
        return blankToDefault(request == null ? null : request.idempotencyKey(), defaultValue);
    }

    private static String refundIdempotencyKey(PaymentRefundRequest request, String defaultValue) {
        return blankToDefault(request == null ? null : request.idempotencyKey(), defaultValue);
    }

    private static String actionReason(PaymentActionRequest request, String defaultValue) {
        return blankToDefault(request == null ? null : request.reason(), defaultValue);
    }

    private static String actionNote(PaymentActionRequest request) {
        return blankToNull(request == null ? null : request.note());
    }

    private static String refundNote(PaymentRefundRequest request) {
        return blankToNull(request == null ? null : request.note());
    }

    private static String requiredText(String value, String reason) {
        String resolved = blankToNull(value);
        if (resolved == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, reason);
        }
        return resolved;
    }

    private static String blankToDefault(String value, String defaultValue) {
        String resolved = blankToNull(value);
        return resolved == null ? defaultValue : resolved;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
