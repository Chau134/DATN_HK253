package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.order.CancelOrderRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.dto.order.OrderSummaryResponse;
import java.util.List;

public interface OrderService {
    List<OrderSummaryResponse> listOrders(Long userAccountId);

    OrderResponse getOrder(Long userAccountId, Long orderId);

    OrderResponse cancelOrder(Long userAccountId, Long orderId, CancelOrderRequest request);

    OrderResponse confirmReceived(Long userAccountId, Long orderId);
}
