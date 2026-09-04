package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.promotion.CouponResponse;
import com.example.serviceapiecommerce.dto.promotion.CouponValidationRequest;
import com.example.serviceapiecommerce.dto.promotion.CouponValidationResponse;
import com.example.serviceapiecommerce.entity.PromotionCustomerScope;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.CouponService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/coupons")
public class CouponController {
    private final CouponService couponService;

    public CouponController(CouponService couponService) {
        this.couponService = couponService;
    }

    @GetMapping
    public List<CouponResponse> getActiveCoupons(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        Long userAccountId = currentUser == null ? null : currentUser.id();
        return couponService.listAvailableCoupons(userAccountId);
    }

    @PostMapping("/validate")
    public CouponValidationResponse validateCoupon(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody CouponValidationRequest request
    ) {
        return couponService.validateCoupon(currentUser.id(), request);
    }
}

