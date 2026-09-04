package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.order.CheckoutPreviewRequest;
import com.example.serviceapiecommerce.dto.order.CheckoutPreviewResponse;
import com.example.serviceapiecommerce.dto.order.CheckoutRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.CheckoutService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/checkout")
public class CheckoutController {
    private static final Logger log = LoggerFactory.getLogger(CheckoutController.class);

    private final CheckoutService checkoutService;

    public CheckoutController(CheckoutService checkoutService) {
        this.checkoutService = checkoutService;
    }

    @PostMapping
    public OrderResponse checkout(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody CheckoutRequest request
    ) {
        OrderResponse response = checkoutService.checkout(currentUser.id(), request);
        log.info(
                "checkout_success user_id={} cart_id={} order_id={} status={} total={}",
                currentUser.id(),
                request.cartId(),
                response.id(),
                response.status(),
                response.totalAmount()
        );
        return response;
    }

    @PostMapping("/preview")
    public CheckoutPreviewResponse preview(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody CheckoutPreviewRequest request
    ) {
        return checkoutService.preview(currentUser.id(), request);
    }
}
