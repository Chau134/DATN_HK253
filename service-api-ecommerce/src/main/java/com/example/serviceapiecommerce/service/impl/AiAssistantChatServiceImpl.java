package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiChatFeedbackRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatResponse;
import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.response.AiChatFeedbackResponse;
import com.example.serviceapiecommerce.dto.response.AiAssistantChatResponse;
import com.example.serviceapiecommerce.dto.response.ProductCardResponse;
import com.example.serviceapiecommerce.service.AiAssistantChatService;
import com.example.serviceapiecommerce.service.AiProductResolver;
import com.example.serviceapiecommerce.service.AiServiceClient;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class AiAssistantChatServiceImpl implements AiAssistantChatService {
    private static final String WARNING_UNAVAILABLE = "ai_service_unavailable";
    private static final String WARNING_SPRING_BOOT_UNAVAILABLE = "spring_boot_unavailable";
    private static final String FRIENDLY_FALLBACK_MESSAGE =
            "Sorry, the assistant is temporarily unavailable. Please try again in a moment.";

    private final AiServiceClient aiServiceClient;
    private final AiProductResolver productResolver;
    private final AiChatPersistenceService chatPersistenceService;

    public AiAssistantChatServiceImpl(
            AiServiceClient aiServiceClient,
            AiProductResolver productResolver,
            AiChatPersistenceService chatPersistenceService
    ) {
        this.aiServiceClient = aiServiceClient;
        this.productResolver = productResolver;
        this.chatPersistenceService = chatPersistenceService;
    }

    @Override
    public AiAssistantChatResponse chat(AiChatRequest request) {
        AiChatResponse aiResponse = aiServiceClient.chat(request);
        if (aiResponse == null) {
            AiChatResponse unavailableResponse = AiChatResponse.unavailable(request, WARNING_UNAVAILABLE);
            Long chatMessageId = chatPersistenceService.recordChatTurn(request, unavailableResponse, List.of())
                    .orElse(null);
            return unavailable(request, chatMessageId);
        }

        List<AiProductResultDto> rankedResults = aiResponse.productIds();
        List<ProductCardResponse> products = rankedResults.isEmpty()
                ? List.of()
                : productResolver.resolve(rankedResults);
        List<String> warnings = products.isEmpty()
                ? aiResponse.warnings()
                : aiResponse.warnings().stream()
                        .filter(warning -> !WARNING_SPRING_BOOT_UNAVAILABLE.equals(warning))
                        .toList();
        Long chatMessageId = chatPersistenceService.recordChatTurn(request, aiResponse, products)
                .orElse(null);
        return new AiAssistantChatResponse(
                aiResponse.sessionId(),
                chatMessageId,
                aiResponse.message(),
                products,
                aiResponse.filters(),
                aiResponse.rewrittenQuery(),
                warnings
        );
    }

    @Override
    public AiChatFeedbackResponse saveFeedback(AiChatFeedbackRequest request) {
        return chatPersistenceService.saveFeedback(request);
    }

    private static AiAssistantChatResponse unavailable(AiChatRequest request, Long chatMessageId) {
        return new AiAssistantChatResponse(
                request == null ? null : request.sessionId(),
                chatMessageId,
                FRIENDLY_FALLBACK_MESSAGE,
                List.of(),
                null,
                null,
                List.of(WARNING_UNAVAILABLE)
        );
    }
}
