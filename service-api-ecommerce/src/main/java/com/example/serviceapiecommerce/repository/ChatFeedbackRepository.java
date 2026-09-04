package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ChatFeedback;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatFeedbackRepository extends JpaRepository<ChatFeedback, Long> {
    Optional<ChatFeedback> findByChatMessage_Id(Long chatMessageId);
}
