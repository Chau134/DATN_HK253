package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.promotion.AdminCouponRequest;
import com.example.serviceapiecommerce.dto.promotion.CouponRedemptionResponse;
import com.example.serviceapiecommerce.dto.promotion.CouponResponse;
import com.example.serviceapiecommerce.entity.CouponStatus;
import com.example.serviceapiecommerce.service.CouponService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/coupons")
public class AdminCouponController {
    private final CouponService couponService;

    public AdminCouponController(CouponService couponService) {
        this.couponService = couponService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public CouponResponse createCoupon(@Valid @RequestBody AdminCouponRequest request) {
        return couponService.createCoupon(request);
    }

    @GetMapping
    public List<CouponResponse> coupons(@RequestParam(required = false) CouponStatus status) {
        return couponService.listCoupons(status);
    }

    @GetMapping("/{couponId}")
    public CouponResponse coupon(@PathVariable Long couponId) {
        return couponService.getCoupon(couponId);
    }

    @PutMapping("/{couponId}")
    public CouponResponse updateCoupon(
            @PathVariable Long couponId,
            @Valid @RequestBody AdminCouponRequest request
    ) {
        return couponService.updateCoupon(couponId, request);
    }

    @DeleteMapping("/{couponId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void archiveCoupon(@PathVariable Long couponId) {
        couponService.archiveCoupon(couponId);
    }

    @GetMapping("/{couponId}/redemptions")
    public List<CouponRedemptionResponse> couponRedemptions(@PathVariable Long couponId) {
        return couponService.listRedemptions(couponId);
    }
}
