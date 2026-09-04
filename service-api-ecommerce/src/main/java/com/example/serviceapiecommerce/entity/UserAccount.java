package com.example.serviceapiecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.Set;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;

@Getter
@Setter
@Entity
@Table(
        name = "user_accounts",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_user_accounts_email", columnNames = "email"),
                @UniqueConstraint(name = "uk_user_accounts_phone_number", columnNames = "phone_number")
        },
        indexes = {
                @Index(name = "idx_user_accounts_status", columnList = "status"),
                @Index(name = "idx_user_accounts_created_at", columnList = "created_at")
        }
)
public class UserAccount {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @Column(name = "email", nullable = false, length = 320)
    private String email;

    @Column(name = "phone_number", length = 30)
    private String phoneNumber;

    @Column(name = "password_hash", nullable = false)
    private String passwordHash;

    @ColumnDefault("1")
    @Column(name = "password_login_enabled")
    private Boolean passwordLoginEnabled;

    @Column(name = "full_name", length = 150)
    private String fullName;

    @Column(name = "display_name", length = 150)
    private String displayName;

    @Enumerated(EnumType.STRING)
    @ColumnDefault("'ACTIVE'")
    @Column(name = "status", nullable = false, length = 50, columnDefinition = "varchar(50)")
    private UserAccountStatus status;

    @ColumnDefault("0")
    @Column(name = "email_verified")
    private Boolean emailVerified;

    @ColumnDefault("0")
    @Column(name = "phone_verified")
    private Boolean phoneVerified;

    @Column(name = "last_login_at")
    private Instant lastLoginAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;

    @ManyToMany
    @JoinTable(
            name = "user_account_roles",
            joinColumns = @JoinColumn(name = "user_account_id"),
            inverseJoinColumns = @JoinColumn(name = "role_id"),
            uniqueConstraints = @UniqueConstraint(
                    name = "uk_user_account_roles_account_role",
                    columnNames = {"user_account_id", "role_id"}
            ),
            indexes = {
                    @Index(name = "idx_user_account_roles_account_id", columnList = "user_account_id"),
                    @Index(name = "idx_user_account_roles_role_id", columnList = "role_id")
            }
    )
    private Set<UserRole> roles = new LinkedHashSet<>();
}
