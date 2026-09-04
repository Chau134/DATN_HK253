package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.admin.AdminOrderStatusRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.dto.order.OrderSummaryResponse;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.entity.OrderStatusHistory;
import com.example.serviceapiecommerce.repository.OrderRepository;
import com.example.serviceapiecommerce.repository.OrderStatusHistoryRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.AdminOrderService;
import com.example.serviceapiecommerce.service.CouponService;
import com.example.serviceapiecommerce.service.InventoryService;
import java.time.Instant;
import java.util.EnumSet;
import java.util.List;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AdminOrderServiceImpl implements AdminOrderService {
    private static final EnumSet<OrderStatus> ADMIN_CANCELLABLE_STATUSES =
            EnumSet.of(OrderStatus.PENDING, OrderStatus.CONFIRMED);

    private final OrderRepository orderRepository;
    private final OrderStatusHistoryRepository orderStatusHistoryRepository;
    private final UserAccountRepository userAccountRepository;
    private final OrderResponseMapper orderResponseMapper;
    private final InventoryService inventoryService;
    private final CouponService couponService;

    public AdminOrderServiceImpl(
            OrderRepository orderRepository,
            OrderStatusHistoryRepository orderStatusHistoryRepository,
            UserAccountRepository userAccountRepository,
            OrderResponseMapper orderResponseMapper,
            InventoryService inventoryService,
            CouponService couponService
    ) {
        this.orderRepository = orderRepository;
        this.orderStatusHistoryRepository = orderStatusHistoryRepository;
        this.userAccountRepository = userAccountRepository;
        this.orderResponseMapper = orderResponseMapper;
        this.inventoryService = inventoryService;
        this.couponService = couponService;
    }

    @Override
    @Transactional(readOnly = true)
    public List<OrderSummaryResponse> listOrders(OrderStatus status) {
        List<Order> orders = status == null
                ? orderRepository.findAll(Sort.by(Sort.Direction.DESC, "createdAt", "id"))
                : orderRepository.findByStatusOrderByCreatedAtDescIdDesc(status);
        return orderResponseMapper.toSummaries(orders);
    }

    @Override
    @Transactional(readOnly = true)
    public OrderResponse getOrder(Long orderId) {
        return orderResponseMapper.toResponse(order(orderId));
    }

    @Override
    @Transactional
    public OrderResponse updateOrderStatus(Long adminUserAccountId, Long orderId, AdminOrderStatusRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "order_status_request_required");
        }
        Order order = lockedOrder(orderId);
        OrderStatus toStatus = request.status();
        if (order.getStatus() == toStatus) {
            return orderResponseMapper.toResponse(order);
        }

        validateTransition(order.getStatus(), toStatus);
        Instant now = Instant.now();
        String reason = blankToDefault(request.reason(), "admin_order_status_update");
        String note = blankToNull(request.note());

        if (toStatus == OrderStatus.CANCELLED) {
            inventoryService.releaseOrCancelOrderStock(order.getId(), adminUserAccountId, reason);
            couponService.cancelOrderRedemptions(order.getId(), reason, now);
        }

        transitionOrder(order, toStatus, adminUserAccountId, reason, note, now);
        return orderResponseMapper.toResponse(order);
    }

    private void validateTransition(OrderStatus fromStatus, OrderStatus toStatus) {
        if (toStatus == OrderStatus.PAID || toStatus == OrderStatus.REFUNDED) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_status_managed_by_payment");
        }
        if (toStatus == OrderStatus.PENDING) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_cannot_revert_to_pending");
        }
        if (toStatus == OrderStatus.CONFIRMED && fromStatus == OrderStatus.PENDING) {
            return;
        }
        if (toStatus == OrderStatus.PACKING && fromStatus == OrderStatus.PAID) {
            return;
        }
        if (toStatus == OrderStatus.SHIPPING && fromStatus == OrderStatus.PACKING) {
            return;
        }
        if (toStatus == OrderStatus.DELIVERED && fromStatus == OrderStatus.SHIPPING) {
            return;
        }
        if (toStatus == OrderStatus.CANCELLED && ADMIN_CANCELLABLE_STATUSES.contains(fromStatus)) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.CONFLICT, "order_status_transition_invalid");
    }

    private void transitionOrder(
            Order order,
            OrderStatus toStatus,
            Long adminUserAccountId,
            String reason,
            String note,
            Instant now
    ) {
        OrderStatus fromStatus = order.getStatus();
        order.setStatus(toStatus);
        order.setUpdatedAt(now);
        if (note != null) {
            order.setAdminNote(note);
        }
        if (toStatus == OrderStatus.CONFIRMED) {
            order.setConfirmedAt(now);
        } else if (toStatus == OrderStatus.CANCELLED) {
            order.setCancelledAt(now);
        }
        orderRepository.save(order);

        OrderStatusHistory history = new OrderStatusHistory();
        history.setOrder(order);
        history.setFromStatus(fromStatus);
        history.setToStatus(toStatus);
        history.setChangedByUserAccount(userAccountRepository.getReferenceById(adminUserAccountId));
        history.setReason(reason);
        history.setNote(note);
        history.setCreatedAt(now);
        orderStatusHistoryRepository.save(history);
    }

    private Order order(Long orderId) {
        if (orderId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "order_id_required");
        }
        return orderRepository.findById(orderId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order_not_found"));
    }

    private Order lockedOrder(Long orderId) {
        if (orderId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "order_id_required");
        }
        return orderRepository.findByIdForUpdate(orderId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order_not_found"));
    }

    private static String blankToDefault(String value, String defaultValue) {
        String resolved = blankToNull(value);
        return resolved == null ? defaultValue : resolved;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
