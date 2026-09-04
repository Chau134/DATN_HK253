package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.admin.AdminOrderStatusRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.dto.order.OrderSummaryResponse;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.AdminOrderService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/orders")
public class AdminOrderController {
    private final AdminOrderService adminOrderService;

    public AdminOrderController(AdminOrderService adminOrderService) {
        this.adminOrderService = adminOrderService;
    }

    @GetMapping
    public List<OrderSummaryResponse> orders(@RequestParam(required = false) OrderStatus status) {
        return adminOrderService.listOrders(status);
    }

    @GetMapping("/{orderId}")
    public OrderResponse order(@PathVariable Long orderId) {
        return adminOrderService.getOrder(orderId);
    }

    @PatchMapping("/{orderId}/status")
    public OrderResponse updateOrderStatus(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long orderId,
            @Valid @RequestBody AdminOrderStatusRequest request
    ) {
        return adminOrderService.updateOrderStatus(currentUser.id(), orderId, request);
    }
}
