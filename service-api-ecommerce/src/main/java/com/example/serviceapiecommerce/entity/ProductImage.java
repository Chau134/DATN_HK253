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
@Table(name = "product_images")
public class ProductImage {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(name = "image_type", nullable = false, length = 50)
    private String imageType;

    @Lob
    @Column(name = "image_url", nullable = false, columnDefinition = "longtext")
    private String imageUrl;

    @ColumnDefault("0")
    @Column(name = "sort_order")
    private Integer sortOrder;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;


}
