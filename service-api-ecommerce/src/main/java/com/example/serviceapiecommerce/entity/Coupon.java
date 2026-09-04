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
import jakarta.persistence.Lob;
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
        name = "coupons",
        uniqueConstraints = @UniqueConstraint(name = "uk_coupons_code", columnNames = "code"),
        indexes = {
                @Index(name = "idx_coupons_status", columnList = "status"),
                @Index(name = "idx_coupons_starts_at", columnList = "starts_at"),
                @Index(name = "idx_coupons_ends_at", columnList = "ends_at"),
                @Index(name = "idx_coupons_customer_scope", columnList = "customer_scope"),
                @Index(name = "idx_coupons_eligible_user_account_id", columnList = "eligible_user_account_id")
        }
)
public class Coupon {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @Column(name = "code", nullable = false, length = 50)
    private String code;

    @Column(name = "name", nullable = false, length = 150)
    private String name;

    @Lob
    @Column(name = "description", columnDefinition = "longtext")
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(name = "discount_type", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private DiscountType discountType;

    @Column(name = "discount_value", nullable = false, precision = 12, scale = 2)
    private BigDecimal discountValue;

    @Column(name = "max_discount_amount", precision = 12, scale = 2)
    private BigDecimal maxDiscountAmount;

    @ColumnDefault("0")
    @Column(name = "min_order_amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal minOrderAmount;

    @ColumnDefault("'VND'")
    @Column(name = "currency", nullable = false, length = 3)
    private String currency;

    @Column(name = "usage_limit")
    private Integer usageLimit;

    @Column(name = "usage_limit_per_user")
    private Integer usageLimitPerUser;

    @ColumnDefault("0")
    @Column(name = "used_count", nullable = false)
    private Integer usedCount;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'ACTIVE'")
    @Column(name = "status", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private CouponStatus status;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'ALL'")
    @Column(name = "customer_scope", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private PromotionCustomerScope customerScope;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "eligible_user_account_id")
    private UserAccount eligibleUserAccount;

    @Column(name = "customer_segment", length = 100)
    private String customerSegment;

    @Column(name = "starts_at")
    private Instant startsAt;

    @Column(name = "ends_at")
    private Instant endsAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;
}
