package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.order.CancelOrderRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.dto.order.OrderSummaryResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.OrderService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/orders")
public class OrderController {
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping
    public List<OrderSummaryResponse> orders(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return orderService.listOrders(currentUser.id());
    }

    @GetMapping("/{orderId}")
    public OrderResponse order(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long orderId
    ) {
        return orderService.getOrder(currentUser.id(), orderId);
    }

    @PostMapping("/{orderId}/cancel")
    public OrderResponse cancelOrder(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long orderId,
            @Valid @RequestBody(required = false) CancelOrderRequest request
    ) {
        return orderService.cancelOrder(currentUser.id(), orderId, request);
    }

    @PostMapping("/{orderId}/received")
    public OrderResponse confirmReceived(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long orderId
    ) {
        return orderService.confirmReceived(currentUser.id(), orderId);
    }
}
