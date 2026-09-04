package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ChatMessage;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {
    List<ChatMessage> findByChatSession_SessionKeyOrderByCreatedAtAscIdAsc(String sessionKey);
}
