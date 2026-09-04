package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.promotion.AdminCouponRequest;
import com.example.serviceapiecommerce.dto.promotion.CouponRedemptionResponse;
import com.example.serviceapiecommerce.dto.promotion.CouponResponse;
import com.example.serviceapiecommerce.dto.promotion.CouponValidationRequest;
import com.example.serviceapiecommerce.dto.promotion.CouponValidationResponse;
import com.example.serviceapiecommerce.entity.Coupon;
import com.example.serviceapiecommerce.entity.CouponRedemption;
import com.example.serviceapiecommerce.entity.CouponRedemptionStatus;
import com.example.serviceapiecommerce.entity.CouponStatus;
import com.example.serviceapiecommerce.entity.DiscountType;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.PromotionCustomerScope;
import com.example.serviceapiecommerce.repository.CouponRedemptionRepository;
import com.example.serviceapiecommerce.repository.CouponRepository;
import com.example.serviceapiecommerce.repository.OrderRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.CouponService;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.Collection;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class CouponServiceImpl implements CouponService {
    private static final String DEFAULT_CURRENCY = "VND";
    private static final BigDecimal ZERO = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
    private static final Collection<CouponRedemptionStatus> ACTIVE_REDEMPTION_STATUSES =
            EnumSet.of(CouponRedemptionStatus.RESERVED, CouponRedemptionStatus.APPLIED);

    private final CouponRepository couponRepository;
    private final CouponRedemptionRepository couponRedemptionRepository;
    private final OrderRepository orderRepository;
    private final UserAccountRepository userAccountRepository;

    public CouponServiceImpl(
            CouponRepository couponRepository,
            CouponRedemptionRepository couponRedemptionRepository,
            OrderRepository orderRepository,
            UserAccountRepository userAccountRepository
    ) {
        this.couponRepository = couponRepository;
        this.couponRedemptionRepository = couponRedemptionRepository;
        this.orderRepository = orderRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @Override
    @Transactional
    public CouponResponse createCoupon(AdminCouponRequest request) {
        requireRequest(request);
        String code = normalizeCode(request.code());
        if (couponRepository.existsByCodeIgnoreCase(code)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_code_exists");
        }

        Instant now = Instant.now();
        Coupon coupon = new Coupon();
        applyRequest(coupon, request, now, true);
        coupon.setCode(code);
        coupon.setUsedCount(0);
        coupon.setCreatedAt(now);
        coupon.setUpdatedAt(now);
        return toResponse(couponRepository.save(coupon));
    }

    @Override
    @Transactional
    public CouponResponse updateCoupon(Long couponId, AdminCouponRequest request) {
        requireRequest(request);
        Coupon coupon = coupon(couponId);
        String code = normalizeCode(request.code());
        couponRepository.findByCodeIgnoreCase(code)
                .filter(existing -> !existing.getId().equals(coupon.getId()))
                .ifPresent(existing -> {
                    throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_code_exists");
                });

        coupon.setCode(code);
        applyRequest(coupon, request, Instant.now(), false);
        return toResponse(couponRepository.save(coupon));
    }

    @Override
    @Transactional(readOnly = true)
    public List<CouponResponse> listCoupons(CouponStatus status) {
        List<Coupon> coupons = status == null
                ? couponRepository.findAllByOrderByCreatedAtDescIdDesc()
                : couponRepository.findByStatusOrderByCreatedAtDescIdDesc(status);
        return coupons.stream()
                .map(CouponServiceImpl::toResponse)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public CouponResponse getCoupon(Long couponId) {
        return toResponse(coupon(couponId));
    }

    @Override
    @Transactional
    public void archiveCoupon(Long couponId) {
        Coupon coupon = coupon(couponId);
        coupon.setStatus(CouponStatus.ARCHIVED);
        coupon.setUpdatedAt(Instant.now());
        couponRepository.save(coupon);
    }

    @Override
    @Transactional(readOnly = true)
    public CouponValidationResponse validateCoupon(Long userAccountId, CouponValidationRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "coupon_validation_request_required");
        }
        BigDecimal orderAmount = money(request.orderAmount());
        BigDecimal shippingFee = money(request.shippingFee());
        String currency = blankToDefault(request.currency(), DEFAULT_CURRENCY);
        Coupon coupon = couponRepository.findByCodeIgnoreCase(normalizeCode(request.code()))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "coupon_not_found"));
        validateCouponForUse(coupon, userAccountId, orderAmount, currency, Instant.now(), true);

        BigDecimal discountAmount = calculateDiscount(coupon, orderAmount, shippingFee);
        return new CouponValidationResponse(
                coupon.getId(),
                coupon.getCode(),
                coupon.getDiscountType(),
                money(coupon.getDiscountValue()),
                discountAmount,
                orderAmount,
                shippingFee,
                orderAmount.add(shippingFee).subtract(discountAmount).max(ZERO),
                coupon.getCurrency()
        );
    }

    @Override
    @Transactional
    public CouponRedemption applyCouponToOrder(Long userAccountId, Order order, String couponCode, Instant now) {
        String code = blankToNull(couponCode);
        if (code == null) {
            return null;
        }
        if (order == null || order.getId() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "order_required");
        }

        Coupon coupon = couponRepository.findByCodeIgnoreCaseForUpdate(normalizeCode(code))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "coupon_not_found"));
        var existing = couponRedemptionRepository.findByCoupon_IdAndOrder_Id(coupon.getId(), order.getId());
        if (existing.isPresent()) {
            return existing.get();
        }

        BigDecimal orderAmount = money(order.getSubtotalAmount());
        BigDecimal currentTotal = money(order.getTotalAmount());
        BigDecimal shippingFee = money(order.getShippingFee());
        String currency = blankToDefault(order.getCurrency(), DEFAULT_CURRENCY);
        Instant resolvedNow = now == null ? Instant.now() : now;

        validateCouponForUse(coupon, userAccountId, orderAmount, currency, resolvedNow, true);
        BigDecimal discountAmount = calculateDiscount(coupon, currentTotal, shippingFee);

        CouponRedemption redemption = new CouponRedemption();
        redemption.setCoupon(coupon);
        redemption.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
        redemption.setOrder(order);
        redemption.setRedemptionKey("coupon:" + coupon.getId() + ":order:" + order.getId());
        redemption.setCouponCode(coupon.getCode());
        redemption.setDiscountType(coupon.getDiscountType());
        redemption.setDiscountValue(money(coupon.getDiscountValue()));
        redemption.setDiscountAmount(discountAmount);
        redemption.setOrderAmount(orderAmount);
        redemption.setCurrency(currency);
        redemption.setStatus(CouponRedemptionStatus.APPLIED);
        redemption.setRedeemedAt(resolvedNow);
        redemption.setCreatedAt(resolvedNow);
        redemption.setUpdatedAt(resolvedNow);

        coupon.setUsedCount(nonNullInt(coupon.getUsedCount()) + 1);
        coupon.setUpdatedAt(resolvedNow);
        couponRepository.save(coupon);

        order.setDiscountAmount(money(order.getDiscountAmount()).add(discountAmount));
        order.setTotalAmount(currentTotal.subtract(discountAmount).max(ZERO));
        order.setUpdatedAt(resolvedNow);
        orderRepository.save(order);
        return couponRedemptionRepository.save(redemption);
    }

    @Override
    @Transactional
    public void cancelOrderRedemptions(Long orderId, String reason, Instant now) {
        closeOrderRedemptions(orderId, CouponRedemptionStatus.CANCELLED, reason, now);
    }

    @Override
    @Transactional
    public void refundOrderRedemptions(Long orderId, String reason, Instant now) {
        closeOrderRedemptions(orderId, CouponRedemptionStatus.REFUNDED, reason, now);
    }

    @Override
    @Transactional(readOnly = true)
    public List<CouponRedemptionResponse> listRedemptions(Long couponId) {
        if (couponId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "coupon_id_required");
        }
        return couponRedemptionRepository.findByCoupon_IdOrderByCreatedAtDescIdDesc(couponId).stream()
                .map(CouponServiceImpl::toRedemptionResponse)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public List<CouponResponse> listAvailableCoupons(Long userAccountId) {
        List<Coupon> coupons = couponRepository.findByStatusOrderByCreatedAtDescIdDesc(CouponStatus.ACTIVE);
        Map<Long, Long> usageByCouponId = usageByCouponId(coupons, userAccountId);
        Instant now = Instant.now();
        return coupons.stream()
                .filter(coupon -> {
                    // 1. Time window checks
                    if (coupon.getStartsAt() != null && coupon.getStartsAt().isAfter(now)) {
                        return false;
                    }
                    if (coupon.getEndsAt() != null && !coupon.getEndsAt().isAfter(now)) {
                        return false;
                    }
                    // 2. Global usage limit check
                    if (coupon.getUsageLimit() != null && nonNullInt(coupon.getUsedCount()) >= coupon.getUsageLimit()) {
                        return false;
                    }
                    // 3. User eligibility check
                    if (!customerEligible(coupon, userAccountId)) {
                        return false;
                    }
                    // 4. Per-user usage limit check
                    if (userAccountId != null && coupon.getUsageLimitPerUser() != null) {
                        long usedByUser = usageByCouponId.getOrDefault(coupon.getId(), 0L);
                        if (usedByUser >= coupon.getUsageLimitPerUser()) {
                            return false;
                        }
                    }
                    return true;
                })
                .map(CouponServiceImpl::toResponse)
                .toList();
    }

    private Map<Long, Long> usageByCouponId(List<Coupon> coupons, Long userAccountId) {
        if (userAccountId == null || coupons.isEmpty()) {
            return Map.of();
        }
        List<Long> couponIds = coupons.stream().map(Coupon::getId).toList();
        Map<Long, Long> result = new LinkedHashMap<>();
        for (CouponRedemptionRepository.CouponUsageCount count :
                couponRedemptionRepository.countUsageByCouponIdsAndUser(
                        couponIds,
                        userAccountId,
                        ACTIVE_REDEMPTION_STATUSES
                )) {
            result.put(count.getCouponId(), count.getRedemptionCount());
        }
        return result;
    }


    private void closeOrderRedemptions(
            Long orderId,
            CouponRedemptionStatus status,
            String reason,
            Instant now
    ) {
        if (orderId == null) {
            return;
        }
        Instant resolvedNow = now == null ? Instant.now() : now;
        for (CouponRedemption redemption : couponRedemptionRepository
                .findByOrder_IdAndStatusInOrderByCreatedAtDescIdDesc(orderId, ACTIVE_REDEMPTION_STATUSES)) {
            Coupon coupon = couponRepository.findByIdForUpdate(redemption.getCoupon().getId())
                    .orElse(redemption.getCoupon());
            coupon.setUsedCount(Math.max(0, nonNullInt(coupon.getUsedCount()) - 1));
            coupon.setUpdatedAt(resolvedNow);
            couponRepository.save(coupon);

            redemption.setStatus(status);
            redemption.setCancelledAt(status == CouponRedemptionStatus.CANCELLED ? resolvedNow : null);
            redemption.setCancelReason(blankToDefault(reason, status.name().toLowerCase()));
            redemption.setUpdatedAt(resolvedNow);
            couponRedemptionRepository.save(redemption);
        }
    }

    private void applyRequest(Coupon coupon, AdminCouponRequest request, Instant now, boolean creating) {
        validateWindow(request.startsAt(), request.endsAt());
        coupon.setName(request.name().trim());
        coupon.setDescription(blankToNull(request.description()));
        coupon.setDiscountType(request.discountType());
        coupon.setDiscountValue(money(request.discountValue()));
        coupon.setMaxDiscountAmount(nullableMoney(request.maxDiscountAmount()));
        coupon.setMinOrderAmount(money(request.minOrderAmount()));
        coupon.setCurrency(blankToDefault(request.currency(), DEFAULT_CURRENCY).toUpperCase());
        coupon.setUsageLimit(request.usageLimit());
        coupon.setUsageLimitPerUser(request.usageLimitPerUser());
        coupon.setStatus(request.status() == null ? (creating ? CouponStatus.ACTIVE : coupon.getStatus()) : request.status());
        coupon.setCustomerScope(request.customerScope() == null
                ? (creating ? PromotionCustomerScope.ALL : coupon.getCustomerScope())
                : request.customerScope());
        coupon.setEligibleUserAccount(request.eligibleUserAccountId() == null
                ? null
                : userAccountRepository.findById(request.eligibleUserAccountId())
                        .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "eligible_user_not_found")));
        coupon.setCustomerSegment(blankToNull(request.customerSegment()));
        coupon.setStartsAt(request.startsAt());
        coupon.setEndsAt(request.endsAt());
        coupon.setUpdatedAt(now);
    }

    private void validateCouponForUse(
            Coupon coupon,
            Long userAccountId,
            BigDecimal orderAmount,
            String currency,
            Instant now,
            boolean includeUsageLimits
    ) {
        if (coupon.getStatus() != CouponStatus.ACTIVE) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_not_active");
        }
        if (coupon.getStartsAt() != null && coupon.getStartsAt().isAfter(now)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_not_started");
        }
        if (coupon.getEndsAt() != null && !coupon.getEndsAt().isAfter(now)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_expired");
        }
        if (!blankToDefault(coupon.getCurrency(), DEFAULT_CURRENCY).equalsIgnoreCase(currency)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_currency_mismatch");
        }
        if (orderAmount.compareTo(money(coupon.getMinOrderAmount())) < 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_min_order_not_met");
        }
        if (!customerEligible(coupon, userAccountId)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_customer_not_eligible");
        }
        if (!includeUsageLimits) {
            return;
        }
        if (coupon.getUsageLimit() != null && nonNullInt(coupon.getUsedCount()) >= coupon.getUsageLimit()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_usage_limit_reached");
        }
        if (coupon.getUsageLimitPerUser() != null) {
            long usedByUser = couponRedemptionRepository.countByCoupon_IdAndUserAccount_IdAndStatusIn(
                    coupon.getId(),
                    userAccountId,
                    ACTIVE_REDEMPTION_STATUSES
            );
            if (usedByUser >= coupon.getUsageLimitPerUser()) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "coupon_user_usage_limit_reached");
            }
        }
    }

    private boolean customerEligible(Coupon coupon, Long userAccountId) {
        PromotionCustomerScope scope = coupon.getCustomerScope() == null
                ? PromotionCustomerScope.ALL
                : coupon.getCustomerScope();
        if (scope == PromotionCustomerScope.ALL) {
            return true;
        }
        if (scope == PromotionCustomerScope.SPECIFIC_CUSTOMER) {
            return coupon.getEligibleUserAccount() != null
                    && coupon.getEligibleUserAccount().getId().equals(userAccountId);
        }
        return false;
    }

    private static BigDecimal calculateDiscount(Coupon coupon, BigDecimal orderAmount, BigDecimal shippingFee) {
        BigDecimal base = coupon.getDiscountType() == DiscountType.FREE_SHIPPING
                ? money(shippingFee)
                : money(orderAmount);
        BigDecimal discount;
        if (coupon.getDiscountType() == DiscountType.PERCENTAGE) {
            discount = base.multiply(money(coupon.getDiscountValue()))
                    .divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP);
        } else if (coupon.getDiscountType() == DiscountType.FIXED_AMOUNT) {
            discount = money(coupon.getDiscountValue());
        } else {
            discount = base;
        }
        if (coupon.getMaxDiscountAmount() != null) {
            discount = discount.min(money(coupon.getMaxDiscountAmount()));
        }
        return discount.min(base).max(ZERO).setScale(2, RoundingMode.HALF_UP);
    }

    private Coupon coupon(Long couponId) {
        if (couponId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "coupon_id_required");
        }
        return couponRepository.findById(couponId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "coupon_not_found"));
    }

    private static CouponResponse toResponse(Coupon coupon) {
        return new CouponResponse(
                coupon.getId(),
                coupon.getCode(),
                coupon.getName(),
                coupon.getDescription(),
                coupon.getDiscountType(),
                coupon.getDiscountValue(),
                coupon.getMaxDiscountAmount(),
                coupon.getMinOrderAmount(),
                coupon.getCurrency(),
                coupon.getUsageLimit(),
                coupon.getUsageLimitPerUser(),
                coupon.getUsedCount(),
                coupon.getStatus(),
                coupon.getCustomerScope(),
                coupon.getEligibleUserAccount() == null ? null : coupon.getEligibleUserAccount().getId(),
                coupon.getCustomerSegment(),
                coupon.getStartsAt(),
                coupon.getEndsAt(),
                coupon.getCreatedAt(),
                coupon.getUpdatedAt()
        );
    }

    private static CouponRedemptionResponse toRedemptionResponse(CouponRedemption redemption) {
        return new CouponRedemptionResponse(
                redemption.getId(),
                redemption.getCoupon().getId(),
                redemption.getUserAccount().getId(),
                redemption.getOrder() == null ? null : redemption.getOrder().getId(),
                redemption.getRedemptionKey(),
                redemption.getCouponCode(),
                redemption.getDiscountType(),
                redemption.getDiscountValue(),
                redemption.getDiscountAmount(),
                redemption.getOrderAmount(),
                redemption.getCurrency(),
                redemption.getStatus(),
                redemption.getRedeemedAt(),
                redemption.getCancelledAt(),
                redemption.getCancelReason(),
                redemption.getCreatedAt(),
                redemption.getUpdatedAt()
        );
    }

    private static void requireRequest(AdminCouponRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "coupon_request_required");
        }
    }

    private static void validateWindow(Instant startsAt, Instant endsAt) {
        if (startsAt != null && endsAt != null && !startsAt.isBefore(endsAt)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "coupon_invalid_time_window");
        }
    }

    private static BigDecimal nullableMoney(BigDecimal value) {
        return value == null ? null : money(value);
    }

    private static BigDecimal money(BigDecimal value) {
        return value == null ? ZERO : value.setScale(2, RoundingMode.HALF_UP);
    }

    private static int nonNullInt(Integer value) {
        return value == null ? 0 : value;
    }

    private static String normalizeCode(String value) {
        String code = blankToNull(value);
        if (code == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "coupon_code_required");
        }
        return code.toUpperCase();
    }

    private static String blankToDefault(String value, String defaultValue) {
        String resolved = blankToNull(value);
        return resolved == null ? defaultValue : resolved;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
