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
        name = "payment_webhook_events",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_payment_webhook_events_provider_event",
                columnNames = {"provider", "event_id"}
        ),
        indexes = {
                @Index(name = "idx_payment_webhook_events_payment_id", columnList = "payment_id"),
                @Index(name = "idx_payment_webhook_events_transaction_id", columnList = "payment_transaction_id"),
                @Index(name = "idx_payment_webhook_events_status", columnList = "processing_status"),
                @Index(name = "idx_payment_webhook_events_event_type", columnList = "event_type"),
                @Index(name = "idx_payment_webhook_events_received_at", columnList = "received_at")
        }
)
public class PaymentWebhookEvent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @Column(name = "provider", nullable = false, length = 50)
    private String provider;

    @Column(name = "event_id", nullable = false, length = 150)
    private String eventId;

    @Column(name = "event_type", length = 100)
    private String eventType;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "payment_id")
    private Payment payment;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "payment_transaction_id")
    private PaymentTransaction paymentTransaction;

    @Column(name = "gateway_payment_id", length = 150)
    private String gatewayPaymentId;

    @Column(name = "gateway_transaction_id", length = 150)
    private String gatewayTransactionId;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'RECEIVED'")
    @Column(name = "processing_status", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private PaymentWebhookEventStatus processingStatus;

    @Lob
    @Column(name = "headers", columnDefinition = "longtext")
    private String headers;

    @Lob
    @Column(name = "payload", nullable = false, columnDefinition = "longtext")
    private String payload;

    @Column(name = "signature", length = 255)
    private String signature;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "received_at")
    private Instant receivedAt;

    @Column(name = "processed_at")
    private Instant processedAt;

    @Lob
    @Column(name = "error_message", columnDefinition = "longtext")
    private String errorMessage;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;
}
