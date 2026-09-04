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
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.math.BigDecimal;
import java.time.Instant;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

@Getter
@Setter
@Entity
@Table(
        name = "chat_message_products",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_chat_message_products_message_rank",
                columnNames = {"chat_message_id", "rank_position"}
        ),
        indexes = {
                @Index(name = "idx_chat_message_products_message_id", columnList = "chat_message_id"),
                @Index(name = "idx_chat_message_products_product_id", columnList = "product_id")
        }
)
public class ChatMessageProduct {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "chat_message_id", nullable = false)
    private ChatMessage chatMessage;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "product_id")
    private Product product;

    @Column(name = "ai_product_id", nullable = false, length = 120)
    private String aiProductId;

    @Column(name = "rank_position", nullable = false)
    private Integer rankPosition;

    @Column(name = "score", precision = 12, scale = 6)
    private BigDecimal score;

    @Column(name = "source", length = 50)
    private String source;

    @Lob
    @Column(name = "product_snapshot_json", columnDefinition = "longtext")
    private String productSnapshotJson;

    @Column(name = "created_at")
    private Instant createdAt;

    @PrePersist
    void prePersist() {
        createdAt = createdAt == null ? Instant.now() : createdAt;
    }
}
