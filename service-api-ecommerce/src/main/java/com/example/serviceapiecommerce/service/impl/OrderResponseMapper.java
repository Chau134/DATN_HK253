package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.order.OrderAddressResponse;
import com.example.serviceapiecommerce.dto.order.OrderItemResponse;
import com.example.serviceapiecommerce.dto.order.OrderPaymentSummaryResponse;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.dto.order.OrderStatusHistoryResponse;
import com.example.serviceapiecommerce.dto.order.OrderSummaryResponse;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderAddress;
import com.example.serviceapiecommerce.entity.OrderItem;
import com.example.serviceapiecommerce.entity.OrderStatusHistory;
import com.example.serviceapiecommerce.entity.Payment;
import com.example.serviceapiecommerce.repository.OrderAddressRepository;
import com.example.serviceapiecommerce.repository.OrderItemRepository;
import com.example.serviceapiecommerce.repository.OrderStatusHistoryRepository;
import com.example.serviceapiecommerce.repository.PaymentRepository;
import com.example.serviceapiecommerce.repository.ProductReviewRepository;
import java.util.Collection;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class OrderResponseMapper {
    private final OrderItemRepository orderItemRepository;
    private final OrderAddressRepository orderAddressRepository;
    private final OrderStatusHistoryRepository orderStatusHistoryRepository;
    private final PaymentRepository paymentRepository;
    private final ProductReviewRepository productReviewRepository;

    public OrderResponseMapper(
            OrderItemRepository orderItemRepository,
            OrderAddressRepository orderAddressRepository,
            OrderStatusHistoryRepository orderStatusHistoryRepository,
            PaymentRepository paymentRepository,
            ProductReviewRepository productReviewRepository
    ) {
        this.orderItemRepository = orderItemRepository;
        this.orderAddressRepository = orderAddressRepository;
        this.orderStatusHistoryRepository = orderStatusHistoryRepository;
        this.paymentRepository = paymentRepository;
        this.productReviewRepository = productReviewRepository;
    }

    public OrderResponse toResponse(Order order) {
        List<OrderItem> items = orderItemRepository.findByOrderIdWithProductData(order.getId());
        Set<Long> reviewedItemIds = reviewedItemIds(items);
        boolean isReviewed = allItemsReviewed(order, reviewedItemIds.size());
        return new OrderResponse(
                order.getId(),
                order.getOrderNumber(),
                order.getStatus(),
                order.getCurrency(),
                order.getItemCount(),
                order.getSubtotalAmount(),
                order.getDiscountAmount(),
                order.getShippingFee(),
                order.getTaxAmount(),
                order.getTotalAmount(),
                latestPayment(order.getId()),
                order.getCustomerNote(),
                order.getPlacedAt(),
                order.getCancelledAt(),
                items.stream()
                        .map(item -> toItem(item, reviewedItemIds.contains(item.getId())))
                        .toList(),
                orderAddressRepository.findByOrder_IdOrderByAddressTypeAscIdAsc(order.getId()).stream()
                        .map(OrderResponseMapper::toAddress)
                        .toList(),
                orderStatusHistoryRepository.findByOrder_IdOrderByCreatedAtAscIdAsc(order.getId()).stream()
                        .map(OrderResponseMapper::toHistory)
                        .toList(),
                order.getCreatedAt(),
                order.getUpdatedAt(),
                isReviewed
        );
    }

    public OrderSummaryResponse toSummary(Order order) {
        return toSummary(
                order,
                latestPayment(order.getId()),
                allItemsReviewed(order, productReviewRepository.countByOrder_Id(order.getId()))
        );
    }

    public List<OrderSummaryResponse> toSummaries(List<Order> orders) {
        if (orders.isEmpty()) {
            return List.of();
        }
        List<Long> orderIds = orders.stream().map(Order::getId).toList();
        Map<Long, OrderPaymentSummaryResponse> latestPayments = latestPayments(orderIds);
        Map<Long, Long> reviewCounts = new LinkedHashMap<>();
        for (ProductReviewRepository.OrderReviewCount count : productReviewRepository.countByOrderIds(orderIds)) {
            reviewCounts.put(count.getOrderId(), count.getReviewCount());
        }
        return orders.stream()
                .map(order -> toSummary(
                        order,
                        latestPayments.get(order.getId()),
                        allItemsReviewed(order, reviewCounts.getOrDefault(order.getId(), 0L))
                ))
                .toList();
    }

    private OrderSummaryResponse toSummary(
            Order order,
            OrderPaymentSummaryResponse latestPayment,
            boolean isReviewed
    ) {
        return new OrderSummaryResponse(
                order.getId(),
                order.getOrderNumber(),
                order.getStatus(),
                order.getCurrency(),
                order.getItemCount(),
                order.getTotalAmount(),
                latestPayment,
                order.getPlacedAt(),
                order.getCreatedAt(),
                order.getUpdatedAt(),
                isReviewed
        );
    }

    private OrderPaymentSummaryResponse latestPayment(Long orderId) {
        return paymentRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId).stream()
                .findFirst()
                .map(OrderResponseMapper::toPaymentSummary)
                .orElse(null);
    }

    private Map<Long, OrderPaymentSummaryResponse> latestPayments(Collection<Long> orderIds) {
        Map<Long, OrderPaymentSummaryResponse> latestByOrderId = new LinkedHashMap<>();
        for (Payment payment : paymentRepository.findByOrderIdsOrderByLatest(orderIds)) {
            latestByOrderId.putIfAbsent(payment.getOrder().getId(), toPaymentSummary(payment));
        }
        return latestByOrderId;
    }

    private Set<Long> reviewedItemIds(List<OrderItem> items) {
        if (items.isEmpty()) {
            return Set.of();
        }
        List<Long> itemIds = items.stream().map(OrderItem::getId).toList();
        return new HashSet<>(productReviewRepository.findReviewedOrderItemIds(itemIds));
    }

    private static OrderPaymentSummaryResponse toPaymentSummary(Payment payment) {
        return new OrderPaymentSummaryResponse(
                payment.getId(),
                payment.getPaymentNumber(),
                payment.getMethod(),
                payment.getStatus(),
                payment.getAmount(),
                payment.getCurrency(),
                payment.getRequestedAt(),
                payment.getPaidAt()
        );
    }

    private static boolean allItemsReviewed(Order order, long reviewCount) {
        return order.getItemCount() != null && reviewCount == order.getItemCount().longValue();
    }

    private OrderItemResponse toItem(OrderItem item, boolean reviewed) {
        return new OrderItemResponse(
                item.getId(),
                item.getSourceProductId(),
                item.getSourceProductVariantId(),
                item.getSkuId(),
                item.getProductTitle(),
                item.getProductTitleVi(),
                item.getBrandName(),
                item.getVariantName(),
                item.getOptionName(),
                item.getOptionValue(),
                item.getUnifiedSize(),
                item.getImageUrl(),
                item.getQuantity(),
                item.getUnitPrice(),
                item.getDiscountedUnitPrice(),
                item.getEffectiveUnitPrice(),
                item.getLineDiscount(),
                item.getLineSubtotal(),
                item.getLineTotal(),
                item.getCurrency(),
                reviewed
        );
    }

    private static OrderAddressResponse toAddress(OrderAddress address) {
        return new OrderAddressResponse(
                address.getId(),
                address.getAddressType(),
                address.getSourceCustomerAddress() == null ? null : address.getSourceCustomerAddress().getId(),
                address.getRecipientName(),
                address.getPhoneNumber(),
                address.getAddressLine1(),
                address.getAddressLine2(),
                address.getWard(),
                address.getDistrict(),
                address.getCity(),
                address.getProvince(),
                address.getCountryCode(),
                address.getPostalCode()
        );
    }

    private static OrderStatusHistoryResponse toHistory(OrderStatusHistory history) {
        return new OrderStatusHistoryResponse(
                history.getId(),
                history.getFromStatus(),
                history.getToStatus(),
                history.getReason(),
                history.getNote(),
                history.getCreatedAt()
        );
    }
}
