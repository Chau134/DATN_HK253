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
        name = "payment_transactions",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_payment_transactions_idempotency_key", columnNames = "idempotency_key"),
                @UniqueConstraint(
                        name = "uk_payment_transactions_provider_gateway_transaction",
                        columnNames = {"provider", "gateway_transaction_id"}
                )
        },
        indexes = {
                @Index(name = "idx_payment_transactions_payment_id", columnList = "payment_id"),
                @Index(name = "idx_payment_transactions_order_id", columnList = "order_id"),
                @Index(name = "idx_payment_transactions_transaction_type", columnList = "transaction_type"),
                @Index(name = "idx_payment_transactions_status", columnList = "status"),
                @Index(name = "idx_payment_transactions_created_at", columnList = "created_at")
        }
)
public class PaymentTransaction {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "payment_id", nullable = false)
    private Payment payment;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    @Enumerated(EnumType.STRING)
    @Column(name = "transaction_type", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private PaymentTransactionType transactionType;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'PENDING'")
    @Column(name = "status", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private PaymentTransactionStatus status;

    @Column(name = "amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal amount;

    @ColumnDefault("'VND'")
    @Column(name = "currency", nullable = false, length = 3)
    private String currency;

    @Column(name = "provider", length = 50)
    private String provider;

    @Column(name = "gateway_transaction_id", length = 150)
    private String gatewayTransactionId;

    @Column(name = "gateway_payment_id", length = 150)
    private String gatewayPaymentId;

    @Column(name = "idempotency_key", length = 100)
    private String idempotencyKey;

    @Column(name = "failure_code", length = 100)
    private String failureCode;

    @Column(name = "failure_message", length = 255)
    private String failureMessage;

    @Lob
    @Column(name = "request_payload", columnDefinition = "longtext")
    private String requestPayload;

    @Lob
    @Column(name = "response_payload", columnDefinition = "longtext")
    private String responsePayload;

    @Column(name = "processed_at")
    private Instant processedAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;
}
