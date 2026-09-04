package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatFeedbackRequest;
import com.example.serviceapiecommerce.dto.response.AiChatFeedbackResponse;
import com.example.serviceapiecommerce.dto.response.AiAssistantChatResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.AiAssistantChatService;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AiAssistantControllerTest {
    @Mock
    private AiAssistantChatService chatService;

    @Test
    void chatDelegatesToService() {
        AiAssistantController controller = new AiAssistantController(chatService);
        AiChatRequest request = new AiChatRequest(
                "session-1",
                "user-1",
                "request-1",
                1,
                "find a black hoodie",
                Map.<String, Object>of("content_type", "image/png", "data_base64", "abc"),
                null,
                "vi-VN"
        );
        AiAssistantChatResponse expected = new AiAssistantChatResponse(
                "session-1",
                10L,
                "Here are some options.",
                List.of(),
                null,
                "black hoodie",
                List.of()
        );

        AiChatRequest trustedRequest = new AiChatRequest(
                "session-1",
                "guest:user-1",
                "request-1",
                1,
                "find a black hoodie",
                Map.<String, Object>of("content_type", "image/png", "data_base64", "abc"),
                null,
                "vi-VN"
        );
        when(chatService.chat(trustedRequest)).thenReturn(expected);

        AiAssistantChatResponse response = controller.chat(request, null);

        assertThat(response).isEqualTo(expected);
        verify(chatService).chat(trustedRequest);
    }

    @Test
    void chatUsesAuthenticatedAccountIdInsteadOfSubmittedUserId() {
        AiAssistantController controller = new AiAssistantController(chatService);
        AiChatRequest request = new AiChatRequest("session-1", "forged-user", "hello", null, null, "vi-VN");
        AiChatRequest trustedRequest = new AiChatRequest("session-1", "42", "hello", null, null, "vi-VN");
        AuthenticatedUser currentUser = new AuthenticatedUser(
                42L,
                "user@example.com",
                "hash",
                true,
                List.of()
        );
        AiAssistantChatResponse expected = new AiAssistantChatResponse(
                "session-1",
                10L,
                "Hello",
                List.of(),
                null,
                null,
                List.of()
        );
        when(chatService.chat(trustedRequest)).thenReturn(expected);

        AiAssistantChatResponse response = controller.chat(request, currentUser);

        assertThat(response).isEqualTo(expected);
        verify(chatService).chat(trustedRequest);
    }

    @Test
    void feedbackUsesSameTrustedAnonymousNamespaceAsChat() {
        AiAssistantController controller = new AiAssistantController(chatService);
        AiChatFeedbackRequest request = new AiChatFeedbackRequest(10L, "browser-1", 5, true, "helpful", null);
        AiChatFeedbackRequest trustedRequest = new AiChatFeedbackRequest(
                10L,
                "guest:browser-1",
                5,
                true,
                "helpful",
                null
        );
        AiChatFeedbackResponse expected = new AiChatFeedbackResponse(1L, 10L, 5, true, "helpful", null);
        when(chatService.saveFeedback(trustedRequest)).thenReturn(expected);

        AiChatFeedbackResponse response = controller.feedback(request, null);

        assertThat(response).isEqualTo(expected);
        verify(chatService).saveFeedback(trustedRequest);
    }
}
