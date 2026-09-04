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
        name = "product_reviews",
        uniqueConstraints = @UniqueConstraint(name = "uk_product_reviews_order_item", columnNames = "order_item_id"),
        indexes = {
                @Index(name = "idx_product_reviews_product_status", columnList = "product_id,status"),
                @Index(name = "idx_product_reviews_user_account_id", columnList = "user_account_id"),
                @Index(name = "idx_product_reviews_order_id", columnList = "order_id"),
                @Index(name = "idx_product_reviews_rating", columnList = "rating"),
                @Index(name = "idx_product_reviews_status", columnList = "status"),
                @Index(name = "idx_product_reviews_created_at", columnList = "created_at")
        }
)
public class ProductReview {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "product_variant_id")
    private ProductVariant productVariant;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "user_account_id", nullable = false)
    private UserAccount userAccount;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "order_id")
    private Order order;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "order_item_id")
    private OrderItem orderItem;

    @Column(name = "rating", nullable = false)
    private Integer rating;

    @Column(name = "title", length = 150)
    private String title;

    @Lob
    @Column(name = "content", columnDefinition = "longtext")
    private String content;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'PENDING'")
    @Column(name = "status", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private ProductReviewStatus status;

    @ColumnDefault("0")
    @Column(name = "verified_purchase")
    private Boolean verifiedPurchase;

    @ColumnDefault("0")
    @Column(name = "helpful_count", nullable = false)
    private Integer helpfulCount;

    @ColumnDefault("0")
    @Column(name = "reported_count", nullable = false)
    private Integer reportedCount;

    @Column(name = "moderation_reason", length = 150)
    private String moderationReason;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "moderated_by_user_account_id")
    private UserAccount moderatedByUserAccount;

    @Column(name = "moderated_at")
    private Instant moderatedAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;
}
