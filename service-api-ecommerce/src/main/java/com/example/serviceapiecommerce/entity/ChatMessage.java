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
        name = "chat_messages",
        indexes = {
                @Index(name = "idx_chat_messages_session_created", columnList = "chat_session_id,created_at"),
                @Index(name = "idx_chat_messages_user_account_id", columnList = "user_account_id"),
                @Index(name = "idx_chat_messages_created_at", columnList = "created_at")
        }
)
public class ChatMessage {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.CASCADE)
    @JoinColumn(name = "chat_session_id", nullable = false)
    private ChatSession chatSession;

    @ManyToOne(fetch = FetchType.LAZY)
    @OnDelete(action = OnDeleteAction.SET_NULL)
    @JoinColumn(name = "user_account_id")
    private UserAccount userAccount;

    @Column(name = "external_user_id", length = 120)
    private String externalUserId;

    @Lob
    @Column(name = "user_message", columnDefinition = "longtext")
    private String userMessage;

    @Lob
    @Column(name = "assistant_message", columnDefinition = "longtext")
    private String assistantMessage;

    @Column(name = "image_present", nullable = false)
    private Boolean imagePresent;

    @Lob
    @Column(name = "image_metadata", columnDefinition = "longtext")
    private String imageMetadata;

    @Lob
    @Column(name = "filters_json", columnDefinition = "longtext")
    private String filtersJson;

    @Column(name = "rewritten_query", length = 1000)
    private String rewrittenQuery;

    @Lob
    @Column(name = "warnings_json", columnDefinition = "longtext")
    private String warningsJson;

    @Column(name = "status", nullable = false, length = 50)
    private String status;

    @Column(name = "created_at")
    private Instant createdAt;

    @Column(name = "updated_at")
    private Instant updatedAt;

    @PrePersist
    void prePersist() {
        Instant now = Instant.now();
        createdAt = createdAt == null ? now : createdAt;
        updatedAt = updatedAt == null ? now : updatedAt;
        status = status == null ? "SUCCESS" : status;
        imagePresent = imagePresent != null && imagePresent;
    }

    @PreUpdate
    void preUpdate() {
        updatedAt = Instant.now();
    }
}
