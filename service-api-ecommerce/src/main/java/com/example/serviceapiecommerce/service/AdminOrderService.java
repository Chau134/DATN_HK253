package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.admin.AdminOrderStatusRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.dto.order.OrderSummaryResponse;
import com.example.serviceapiecommerce.entity.OrderStatus;
import java.util.List;

public interface AdminOrderService {
    List<OrderSummaryResponse> listOrders(OrderStatus status);

    OrderResponse getOrder(Long orderId);

    OrderResponse updateOrderStatus(Long adminUserAccountId, Long orderId, AdminOrderStatusRequest request);
}
