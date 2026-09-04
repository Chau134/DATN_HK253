package com.example.serviceapiecommerce.entity;

import jakarta.persistence.CascadeType;
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
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

@Getter
@Setter
@Entity
@Table(
        name = "wishlists",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_wishlists_user_name",
                columnNames = {"user_account_id", "name"}
        ),
        indexes = {
                @Index(name = "idx_wishlists_user_account_id", columnList = "user_account_id"),
                @Index(name = "idx_wishlists_user_status", columnList = "user_account_id,status"),
                @Index(name = "idx_wishlists_updated_at", columnList = "updated_at")
        }
)
public class Wishlist {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "user_account_id", nullable = false)
    private UserAccount userAccount;

    @ColumnDefault("'Default'")
    @Column(name = "name", nullable = false, length = 100)
    private String name;

    @ColumnDefault("1")
    @Column(name = "default_wishlist")
    private Boolean defaultWishlist;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'ACTIVE'")
    @Column(name = "status", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private WishlistStatus status;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;

    @OneToMany(mappedBy = "wishlist", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<WishlistItem> items = new ArrayList<>();
}
