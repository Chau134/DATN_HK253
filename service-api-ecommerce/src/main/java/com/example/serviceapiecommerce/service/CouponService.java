package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.promotion.AdminCouponRequest;
import com.example.serviceapiecommerce.dto.promotion.CouponRedemptionResponse;
import com.example.serviceapiecommerce.dto.promotion.CouponResponse;
import com.example.serviceapiecommerce.dto.promotion.CouponValidationRequest;
import com.example.serviceapiecommerce.dto.promotion.CouponValidationResponse;
import com.example.serviceapiecommerce.entity.CouponRedemption;
import com.example.serviceapiecommerce.entity.CouponStatus;
import com.example.serviceapiecommerce.entity.Order;
import java.time.Instant;
import java.util.List;

public interface CouponService {
    CouponResponse createCoupon(AdminCouponRequest request);

    CouponResponse updateCoupon(Long couponId, AdminCouponRequest request);

    List<CouponResponse> listCoupons(CouponStatus status);

    CouponResponse getCoupon(Long couponId);

    void archiveCoupon(Long couponId);

    CouponValidationResponse validateCoupon(Long userAccountId, CouponValidationRequest request);

    CouponRedemption applyCouponToOrder(Long userAccountId, Order order, String couponCode, Instant now);

    void cancelOrderRedemptions(Long orderId, String reason, Instant now);

    void refundOrderRedemptions(Long orderId, String reason, Instant now);

    List<CouponRedemptionResponse> listRedemptions(Long couponId);

    List<CouponResponse> listAvailableCoupons(Long userAccountId);
}

