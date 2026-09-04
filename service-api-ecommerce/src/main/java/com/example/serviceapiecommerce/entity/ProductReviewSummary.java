package com.example.serviceapiecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
        name = "product_review_summaries",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_product_review_summaries_product",
                columnNames = "product_id"
        ),
        indexes = @Index(name = "idx_product_review_summaries_rating", columnList = "average_rating")
)
public class ProductReviewSummary {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @ColumnDefault("0")
    @Column(name = "review_count", nullable = false)
    private Integer reviewCount;

    @ColumnDefault("0")
    @Column(name = "approved_review_count", nullable = false)
    private Integer approvedReviewCount;

    @ColumnDefault("0")
    @Column(name = "average_rating", nullable = false, precision = 3, scale = 2)
    private BigDecimal averageRating;

    @ColumnDefault("0")
    @Column(name = "rating_1_count", nullable = false)
    private Integer rating1Count;

    @ColumnDefault("0")
    @Column(name = "rating_2_count", nullable = false)
    private Integer rating2Count;

    @ColumnDefault("0")
    @Column(name = "rating_3_count", nullable = false)
    private Integer rating3Count;

    @ColumnDefault("0")
    @Column(name = "rating_4_count", nullable = false)
    private Integer rating4Count;

    @ColumnDefault("0")
    @Column(name = "rating_5_count", nullable = false)
    private Integer rating5Count;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;
}
