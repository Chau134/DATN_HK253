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
        name = "payments",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_payments_payment_number", columnNames = "payment_number"),
                @UniqueConstraint(name = "uk_payments_idempotency_key", columnNames = "idempotency_key"),
                @UniqueConstraint(
                        name = "uk_payments_provider_gateway_payment",
                        columnNames = {"provider", "gateway_payment_id"}
                )
        },
        indexes = {
                @Index(name = "idx_payments_order_id", columnList = "order_id"),
                @Index(name = "idx_payments_user_account_id", columnList = "user_account_id"),
                @Index(name = "idx_payments_status", columnList = "status"),
                @Index(name = "idx_payments_method", columnList = "method"),
                @Index(name = "idx_payments_provider", columnList = "provider"),
                @Index(name = "idx_payments_created_at", columnList = "created_at")
        }
)
public class Payment {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @Column(name = "payment_number", nullable = false, length = 50)
    private String paymentNumber;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "user_account_id", nullable = false)
    private UserAccount userAccount;

    @Enumerated(EnumType.STRING)
    @Column(name = "method", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private PaymentMethod method;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'PENDING'")
    @Column(name = "status", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private PaymentStatus status;

    @Column(name = "amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal amount;

    @ColumnDefault("0")
    @Column(name = "refunded_amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal refundedAmount;

    @ColumnDefault("'VND'")
    @Column(name = "currency", nullable = false, length = 3)
    private String currency;

    @Column(name = "provider", length = 50)
    private String provider;

    @Column(name = "gateway_payment_id", length = 150)
    private String gatewayPaymentId;

    @Column(name = "gateway_order_id", length = 150)
    private String gatewayOrderId;

    @Column(name = "idempotency_key", length = 100)
    private String idempotencyKey;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "requested_at")
    private Instant requestedAt;

    @Column(name = "authorized_at")
    private Instant authorizedAt;

    @Column(name = "paid_at")
    private Instant paidAt;

    @Column(name = "failed_at")
    private Instant failedAt;

    @Column(name = "cancelled_at")
    private Instant cancelledAt;

    @Column(name = "refunded_at")
    private Instant refundedAt;

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "failure_code", length = 100)
    private String failureCode;

    @Column(name = "failure_message", length = 255)
    private String failureMessage;

    @Lob
    @Column(name = "metadata", columnDefinition = "longtext")
    private String metadata;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;
}
