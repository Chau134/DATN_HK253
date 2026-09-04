package com.example.serviceapiecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
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
        name = "order_items",
        indexes = {
                @Index(name = "idx_order_items_order_id", columnList = "order_id"),
                @Index(name = "idx_order_items_product_id", columnList = "product_id"),
                @Index(name = "idx_order_items_product_variant_id", columnList = "product_variant_id")
        }
)
public class OrderItem {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "order_id", nullable = false)
    private Order order;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id")
    private Product product;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_variant_id")
    private ProductVariant productVariant;

    @Column(name = "source_product_id", nullable = false)
    private Long sourceProductId;

    @Column(name = "source_product_variant_id", nullable = false)
    private Long sourceProductVariantId;

    @Column(name = "sku_id")
    private Long skuId;

    @Column(name = "product_title", nullable = false)
    private String productTitle;

    @Column(name = "product_title_vi")
    private String productTitleVi;

    @Column(name = "brand_name", length = 150)
    private String brandName;

    @Column(name = "variant_name")
    private String variantName;

    @Column(name = "option_name", length = 100)
    private String optionName;

    @Column(name = "option_value", length = 100)
    private String optionValue;

    @Column(name = "unified_size", length = 100)
    private String unifiedSize;

    @Lob
    @Column(name = "image_url", columnDefinition = "longtext")
    private String imageUrl;

    @Column(name = "quantity", nullable = false)
    private Integer quantity;

    @Column(name = "unit_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal unitPrice;

    @Column(name = "discounted_unit_price", precision = 12, scale = 2)
    private BigDecimal discountedUnitPrice;

    @Column(name = "effective_unit_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal effectiveUnitPrice;

    @ColumnDefault("0")
    @Column(name = "line_discount", nullable = false, precision = 12, scale = 2)
    private BigDecimal lineDiscount;

    @Column(name = "line_subtotal", nullable = false, precision = 12, scale = 2)
    private BigDecimal lineSubtotal;

    @Column(name = "line_total", nullable = false, precision = 12, scale = 2)
    private BigDecimal lineTotal;

    @ColumnDefault("'VND'")
    @Column(name = "currency", nullable = false, length = 3)
    private String currency;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;
}
