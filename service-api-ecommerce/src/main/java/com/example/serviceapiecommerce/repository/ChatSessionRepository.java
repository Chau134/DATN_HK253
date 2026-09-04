package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ChatSession;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatSessionRepository extends JpaRepository<ChatSession, Long> {
    Optional<ChatSession> findBySessionKey(String sessionKey);
}
