package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.order.CancelOrderRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.dto.order.OrderSummaryResponse;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.entity.OrderStatusHistory;
import com.example.serviceapiecommerce.entity.Payment;
import com.example.serviceapiecommerce.entity.PaymentMethod;
import com.example.serviceapiecommerce.entity.PaymentStatus;
import com.example.serviceapiecommerce.entity.PaymentTransaction;
import com.example.serviceapiecommerce.entity.PaymentTransactionStatus;
import com.example.serviceapiecommerce.entity.PaymentTransactionType;
import com.example.serviceapiecommerce.repository.OrderRepository;
import com.example.serviceapiecommerce.repository.OrderStatusHistoryRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.repository.PaymentRepository;
import com.example.serviceapiecommerce.repository.PaymentTransactionRepository;
import com.example.serviceapiecommerce.service.CouponService;
import com.example.serviceapiecommerce.service.InventoryService;
import com.example.serviceapiecommerce.service.OrderService;
import java.time.Instant;
import java.util.EnumSet;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class OrderServiceImpl implements OrderService {
    private static final EnumSet<OrderStatus> CUSTOMER_CANCELLABLE_STATUSES =
            EnumSet.of(OrderStatus.PENDING, OrderStatus.CONFIRMED);

    private final OrderRepository orderRepository;
    private final OrderStatusHistoryRepository orderStatusHistoryRepository;
    private final UserAccountRepository userAccountRepository;
    private final OrderResponseMapper orderResponseMapper;
    private final InventoryService inventoryService;
    private final CouponService couponService;
    private final PaymentRepository paymentRepository;
    private final PaymentTransactionRepository paymentTransactionRepository;

    public OrderServiceImpl(
            OrderRepository orderRepository,
            OrderStatusHistoryRepository orderStatusHistoryRepository,
            UserAccountRepository userAccountRepository,
            OrderResponseMapper orderResponseMapper,
            InventoryService inventoryService,
            CouponService couponService,
            PaymentRepository paymentRepository,
            PaymentTransactionRepository paymentTransactionRepository
    ) {
        this.orderRepository = orderRepository;
        this.orderStatusHistoryRepository = orderStatusHistoryRepository;
        this.userAccountRepository = userAccountRepository;
        this.orderResponseMapper = orderResponseMapper;
        this.inventoryService = inventoryService;
        this.couponService = couponService;
        this.paymentRepository = paymentRepository;
        this.paymentTransactionRepository = paymentTransactionRepository;
    }

    @Override
    @Transactional(readOnly = true)
    public List<OrderSummaryResponse> listOrders(Long userAccountId) {
        return orderResponseMapper.toSummaries(
                orderRepository.findByUserAccount_IdOrderByCreatedAtDescIdDesc(userAccountId)
        );
    }

    @Override
    @Transactional(readOnly = true)
    public OrderResponse getOrder(Long userAccountId, Long orderId) {
        return orderResponseMapper.toResponse(findOwnedOrder(userAccountId, orderId));
    }

    @Override
    @Transactional
    public OrderResponse cancelOrder(Long userAccountId, Long orderId, CancelOrderRequest request) {
        Order order = findOwnedOrder(userAccountId, orderId);
        if (order.getStatus() == OrderStatus.CANCELLED) {
            return orderResponseMapper.toResponse(order);
        }
        if (!CUSTOMER_CANCELLABLE_STATUSES.contains(order.getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_cannot_be_cancelled");
        }

        Instant now = Instant.now();
        OrderStatus previousStatus = order.getStatus();
        String reason = hasText(request == null ? null : request.reason())
                ? request.reason().trim()
                : "customer_cancelled";
        inventoryService.releaseOrCancelOrderStock(order.getId(), userAccountId, reason);
        couponService.cancelOrderRedemptions(order.getId(), reason, now);

        order.setStatus(OrderStatus.CANCELLED);
        order.setCancelledAt(now);
        order.setUpdatedAt(now);
        orderRepository.save(order);

        OrderStatusHistory history = new OrderStatusHistory();
        history.setOrder(order);
        history.setFromStatus(previousStatus);
        history.setToStatus(OrderStatus.CANCELLED);
        history.setChangedByUserAccount(userAccountRepository.getReferenceById(userAccountId));
        history.setReason(reason);
        history.setNote(blankToNull(request == null ? null : request.note()));
        history.setCreatedAt(now);
        orderStatusHistoryRepository.save(history);
        return orderResponseMapper.toResponse(order);
    }

    @Override
    @Transactional
    public OrderResponse confirmReceived(Long userAccountId, Long orderId) {
        Order order = lockedOwnedOrder(userAccountId, orderId);
        if (order.getStatus() == OrderStatus.COMPLETED) {
            return orderResponseMapper.toResponse(order);
        }
        if (order.getStatus() != OrderStatus.SHIPPING && order.getStatus() != OrderStatus.DELIVERED) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_not_shipping_or_delivered");
        }

        Instant now = Instant.now();
        OrderStatus previousStatus = order.getStatus();
        order.setStatus(OrderStatus.COMPLETED);
        order.setPaidAt(now);
        order.setUpdatedAt(now);
        orderRepository.save(order);

        OrderStatusHistory history = new OrderStatusHistory();
        history.setOrder(order);
        history.setFromStatus(previousStatus);
        history.setToStatus(OrderStatus.COMPLETED);
        history.setChangedByUserAccount(userAccountRepository.getReferenceById(userAccountId));
        history.setReason("customer_received");
        history.setNote("Customer confirmed received order");
        history.setCreatedAt(now);
        orderStatusHistoryRepository.save(history);

        List<Payment> payments = paymentRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(order.getId());
        for (Payment payment : payments) {
            if (payment.getMethod() == PaymentMethod.COD && payment.getStatus() != PaymentStatus.PAID) {
                payment.setStatus(PaymentStatus.PAID);
                payment.setPaidAt(now);
                payment.setUpdatedAt(now);
                paymentRepository.save(payment);

                PaymentTransaction transaction = new PaymentTransaction();
                transaction.setPayment(payment);
                transaction.setOrder(order);
                transaction.setTransactionType(PaymentTransactionType.CAPTURE);
                transaction.setStatus(PaymentTransactionStatus.SUCCESS);
                transaction.setAmount(payment.getAmount());
                transaction.setCurrency(payment.getCurrency() != null ? payment.getCurrency() : "VND");
                transaction.setProvider(payment.getProvider());
                transaction.setGatewayPaymentId(payment.getGatewayPaymentId());
                transaction.setIdempotencyKey("cod-capture:payment:" + payment.getId());
                transaction.setRequestPayload("customer_received_cod");
                transaction.setProcessedAt(now);
                transaction.setCreatedAt(now);
                paymentTransactionRepository.save(transaction);
            }
        }

        return orderResponseMapper.toResponse(order);
    }

    private Order findOwnedOrder(Long userAccountId, Long orderId) {
        if (orderId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "order_id_required");
        }
        return orderRepository.findByIdAndUserAccount_Id(orderId, userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order_not_found"));
    }

    private Order lockedOwnedOrder(Long userAccountId, Long orderId) {
        if (orderId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "order_id_required");
        }
        return orderRepository.findByIdAndUserAccountIdForUpdate(orderId, userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order_not_found"));
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private static String blankToNull(String value) {
        return hasText(value) ? value.trim() : null;
    }
}
