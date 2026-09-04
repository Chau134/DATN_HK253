package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatExceptionOfType;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.dto.ai.AiChatFeedbackRequest;
import com.example.serviceapiecommerce.entity.ChatMessage;
import com.example.serviceapiecommerce.repository.ChatFeedbackRepository;
import com.example.serviceapiecommerce.repository.ChatMessageProductRepository;
import com.example.serviceapiecommerce.repository.ChatMessageRepository;
import com.example.serviceapiecommerce.repository.ChatSessionRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class AiChatPersistenceServiceFeedbackTest {
    @Mock
    private ChatSessionRepository chatSessionRepository;
    @Mock
    private ChatMessageRepository chatMessageRepository;
    @Mock
    private ChatMessageProductRepository chatMessageProductRepository;
    @Mock
    private ChatFeedbackRepository chatFeedbackRepository;
    @Mock
    private UserAccountRepository userAccountRepository;
    @Mock
    private ProductRepository productRepository;
    @Mock
    private ObjectMapper objectMapper;

    @Test
    void feedbackRejectsAnonymousUserWhoDoesNotOwnMessage() {
        AiChatPersistenceService service = new AiChatPersistenceService(
                chatSessionRepository,
                chatMessageRepository,
                chatMessageProductRepository,
                chatFeedbackRepository,
                userAccountRepository,
                productRepository,
                objectMapper
        );
        ChatMessage message = new ChatMessage();
        message.setId(10L);
        message.setExternalUserId("guest:owner-browser");
        when(chatMessageRepository.findById(10L)).thenReturn(Optional.of(message));

        assertThatExceptionOfType(ResponseStatusException.class)
                .isThrownBy(() -> service.saveFeedback(new AiChatFeedbackRequest(
                        10L,
                        "guest:other-browser",
                        1,
                        false,
                        "not_helpful",
                        null
                )))
                .satisfies(exception -> assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN));
        verifyNoInteractions(chatFeedbackRepository);
    }
}
