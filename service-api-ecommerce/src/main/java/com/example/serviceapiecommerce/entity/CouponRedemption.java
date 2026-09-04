package com.example.serviceapiecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.math.BigDecimal;
import java.time.Instant;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

@Getter
@Setter
@Entity
@Table(
        name = "coupon_redemptions",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_coupon_redemptions_redemption_key", columnNames = "redemption_key"),
                @UniqueConstraint(name = "uk_coupon_redemptions_coupon_order", columnNames = {"coupon_id", "order_id"})
        },
        indexes = {
                @Index(name = "idx_coupon_redemptions_coupon_id", columnList = "coupon_id"),
                @Index(name = "idx_coupon_redemptions_user_account_id", columnList = "user_account_id"),
                @Index(name = "idx_coupon_redemptions_order_id", columnList = "order_id"),
                @Index(name = "idx_coupon_redemptions_status", columnList = "status"),
                @Index(name = "idx_coupon_redemptions_redeemed_at", columnList = "redeemed_at")
        }
)
public class CouponRedemption {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "coupon_id", nullable = false)
    private Coupon coupon;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "user_account_id", nullable = false)
    private UserAccount userAccount;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "order_id")
    private Order order;

    @Column(name = "redemption_key", length = 100)
    private String redemptionKey;

    @Column(name = "coupon_code", nullable = false, length = 50)
    private String couponCode;

    @Enumerated(EnumType.STRING)
    @Column(name = "discount_type", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private DiscountType discountType;

    @Column(name = "discount_value", nullable = false, precision = 12, scale = 2)
    private BigDecimal discountValue;

    @Column(name = "discount_amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal discountAmount;

    @Column(name = "order_amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal orderAmount;

    @ColumnDefault("'VND'")
    @Column(name = "currency", nullable = false, length = 3)
    private String currency;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'RESERVED'")
    @Column(name = "status", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private CouponRedemptionStatus status;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "redeemed_at")
    private Instant redeemedAt;

    @Column(name = "cancelled_at")
    private Instant cancelledAt;

    @Column(name = "cancel_reason", length = 150)
    private String cancelReason;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;
}
