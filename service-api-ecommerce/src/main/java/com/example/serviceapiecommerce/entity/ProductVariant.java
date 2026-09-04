package com.example.serviceapiecommerce.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "product_variants")
public class ProductVariant {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(name = "sku_id")
    private Long skuId;

    @Column(name = "option_name", length = 100)
    private String optionName;

    @Column(name = "option_value", length = 100)
    private String optionValue;

    @Column(name = "unified_size", length = 100)
    private String unifiedSize;

    @ColumnDefault("0")
    @Column(name = "inventory_count")
    private Integer inventoryCount;

    @ColumnDefault("0")
    @Column(name = "available")
    private Boolean available;

    @ColumnDefault("1")
    @Column(name = "active")
    private Boolean active;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;


}
