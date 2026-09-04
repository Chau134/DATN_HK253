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

@Getter
@Setter
@Entity
@Table(
        name = "inventory_movements",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_inventory_movements_idempotency_key",
                columnNames = "idempotency_key"
        ),
        indexes = {
                @Index(name = "idx_inventory_movements_product_variant_id", columnList = "product_variant_id"),
                @Index(name = "idx_inventory_movements_movement_type", columnList = "movement_type"),
                @Index(name = "idx_inventory_movements_order_id", columnList = "order_id"),
                @Index(name = "idx_inventory_movements_reservation_id", columnList = "reservation_id"),
                @Index(name = "idx_inventory_movements_created_at", columnList = "created_at")
        }
)
public class InventoryMovement {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id")
    private Product product;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_variant_id")
    private ProductVariant productVariant;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "reservation_id")
    private InventoryReservation reservation;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id")
    private Order order;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_item_id")
    private OrderItem orderItem;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "changed_by_user_account_id")
    private UserAccount changedByUserAccount;

    @Enumerated(EnumType.STRING)
    @Column(name = "movement_type", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private InventoryMovementType movementType;

    @Column(name = "quantity_delta", nullable = false)
    private Integer quantityDelta;

    @Column(name = "quantity_before")
    private Integer quantityBefore;

    @Column(name = "quantity_after")
    private Integer quantityAfter;

    @Column(name = "reference_type", length = 50)
    private String referenceType;

    @Column(name = "reference_id", length = 100)
    private String referenceId;

    @Column(name = "idempotency_key", length = 100)
    private String idempotencyKey;

    @Column(name = "reason", length = 150)
    private String reason;

    @Lob
    @Column(name = "note", columnDefinition = "longtext")
    private String note;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;
}
