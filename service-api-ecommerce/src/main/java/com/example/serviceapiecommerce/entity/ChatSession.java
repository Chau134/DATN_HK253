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
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

@Getter
@Setter
@Entity
@Table(
        name = "chat_sessions",
        indexes = {
                @Index(name = "idx_chat_sessions_user_account_id", columnList = "user_account_id"),
                @Index(name = "idx_chat_sessions_external_user_id", columnList = "external_user_id"),
                @Index(name = "idx_chat_sessions_last_message_at", columnList = "last_message_at")
        }
)
public class ChatSession {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @Column(name = "session_key", nullable = false, length = 120, unique = true)
    private String sessionKey;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "user_account_id")
    private UserAccount userAccount;

    @Column(name = "external_user_id", length = 120)
    private String externalUserId;

    @Column(name = "locale", nullable = false, length = 20)
    private String locale;

    @Column(name = "status", nullable = false, length = 50)
    private String status;

    @Column(name = "last_message_at")
    private Instant lastMessageAt;

    @Column(name = "created_at")
    private Instant createdAt;

    @Column(name = "updated_at")
    private Instant updatedAt;

    @PrePersist
    void prePersist() {
        Instant now = Instant.now();
        createdAt = createdAt == null ? now : createdAt;
        updatedAt = updatedAt == null ? now : updatedAt;
        status = status == null ? "ACTIVE" : status;
        locale = locale == null || locale.isBlank() ? "vi-VN" : locale;
    }

    @PreUpdate
    void preUpdate() {
        updatedAt = Instant.now();
    }
}
