package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.ai.AiChatFeedbackRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.response.AiChatFeedbackResponse;
import com.example.serviceapiecommerce.dto.response.AiAssistantChatResponse;
import com.example.serviceapiecommerce.service.AiAssistantChatService;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/assistant")
public class AiAssistantController {
    private final AiAssistantChatService chatService;

    public AiAssistantController(AiAssistantChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/chat")
    public AiAssistantChatResponse chat(
            @Valid @RequestBody AiChatRequest request,
            @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        return chatService.chat(withTrustedUser(request, currentUser));
    }

    @PostMapping("/feedback")
    public AiChatFeedbackResponse feedback(
            @Valid @RequestBody AiChatFeedbackRequest request,
            @AuthenticationPrincipal AuthenticatedUser currentUser
    ) {
        return chatService.saveFeedback(withTrustedUser(request, currentUser));
    }

    private static AiChatRequest withTrustedUser(AiChatRequest request, AuthenticatedUser currentUser) {
        return new AiChatRequest(
                request.sessionId(),
                trustedUserId(request.userId(), currentUser),
                request.requestId(),
                request.turnSequence(),
                request.message(),
                request.image(),
                request.cropBox(),
                request.locale()
        );
    }

    private static AiChatFeedbackRequest withTrustedUser(
            AiChatFeedbackRequest request,
            AuthenticatedUser currentUser
    ) {
        return new AiChatFeedbackRequest(
                request.chatMessageId(),
                trustedUserId(request.userId(), currentUser),
                request.rating(),
                request.helpful(),
                request.feedbackType(),
                request.comment()
        );
    }

    private static String trustedUserId(String submittedUserId, AuthenticatedUser currentUser) {
        if (currentUser != null) {
            return String.valueOf(currentUser.id());
        }
        if (submittedUserId == null || submittedUserId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "user_id_required");
        }
        String anonymousId = submittedUserId.startsWith("guest:")
                ? submittedUserId.substring("guest:".length())
                : submittedUserId;
        anonymousId = anonymousId.strip();
        if (anonymousId.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "user_id_required");
        }
        return "guest:" + anonymousId.substring(0, Math.min(anonymousId.length(), 114));
    }
}
