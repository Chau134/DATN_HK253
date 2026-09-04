package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatResponse;
import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.response.ProductCardResponse;
import com.example.serviceapiecommerce.service.AiProductResolver;
import com.example.serviceapiecommerce.service.AiServiceClient;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AiAssistantChatServiceImplTest {
    @Mock
    private AiServiceClient aiServiceClient;

    @Mock
    private AiProductResolver productResolver;

    @Mock
    private AiChatPersistenceService chatPersistenceService;

    @Test
    void chatForwardsToPythonAndResolvesReturnedProducts() {
        AiAssistantChatServiceImpl service = new AiAssistantChatServiceImpl(
                aiServiceClient,
                productResolver,
                chatPersistenceService
        );
        AiChatRequest request = new AiChatRequest(
                "session-1",
                "user-1",
                "find a black hoodie",
                Map.<String, Object>of("content_type", "image/png", "data_base64", "abc"),
                null,
                "vi-VN"
        );
        List<AiProductResultDto> rankedResults = List.of(
                new AiProductResultDto("2", 0.95, "hybrid"),
                new AiProductResultDto("1", 0.90, "hybrid")
        );
        AiChatResponse aiResponse = new AiChatResponse(
                "session-1",
                "Here are some options.",
                rankedResults,
                null,
                "black hoodie",
                List.of()
        );
        List<ProductCardResponse> cards = List.of(card("2"), card("1"));

        when(aiServiceClient.chat(request)).thenReturn(aiResponse);
        when(productResolver.resolve(rankedResults)).thenReturn(cards);
        when(chatPersistenceService.recordChatTurn(request, aiResponse, cards)).thenReturn(Optional.of(10L));

        var response = service.chat(request);

        assertThat(response.sessionId()).isEqualTo("session-1");
        assertThat(response.chatMessageId()).isEqualTo(10L);
        assertThat(response.message()).isEqualTo("Here are some options.");
        assertThat(response.products()).containsExactlyElementsOf(cards);
        assertThat(response.rewrittenQuery()).isEqualTo("black hoodie");
        verify(productResolver).resolve(rankedResults);
    }

    @Test
    void chatReturnsFriendlyFallbackWithoutResolvingProductsWhenPythonUnavailable() {
        AiAssistantChatServiceImpl service = new AiAssistantChatServiceImpl(
                aiServiceClient,
                productResolver,
                chatPersistenceService
        );
        AiChatRequest request = new AiChatRequest("session-1", "user-1", "hello", null, null, "vi-VN");
        AiChatResponse unavailableResponse = AiChatResponse.unavailable(request, "ai_service_unavailable");

        when(aiServiceClient.chat(request)).thenReturn(unavailableResponse);
        when(chatPersistenceService.recordChatTurn(request, unavailableResponse, List.of())).thenReturn(Optional.of(11L));

        var response = service.chat(request);

        assertThat(response.sessionId()).isEqualTo("session-1");
        assertThat(response.chatMessageId()).isEqualTo(11L);
        assertThat(response.message()).contains("assistant is temporarily unavailable");
        assertThat(response.products()).isEmpty();
        assertThat(response.warnings()).containsExactly("ai_service_unavailable");
        verify(productResolver, never()).resolve(List.of());
    }

    @Test
    void chatHidesSpringBootWarningWhenGatewayResolvedProducts() {
        AiAssistantChatServiceImpl service = new AiAssistantChatServiceImpl(
                aiServiceClient,
                productResolver,
                chatPersistenceService
        );
        AiChatRequest request = new AiChatRequest(
                "session-pink-shirt",
                "user-1",
                "find a pink t-shirt",
                null,
                null,
                "vi-VN"
        );
        List<AiProductResultDto> rankedResults = List.of(
                new AiProductResultDto("775", 0.95, "text")
        );
        AiChatResponse aiResponse = new AiChatResponse(
                "session-pink-shirt",
                "The shop has a pink t-shirt.",
                rankedResults,
                null,
                "pink t-shirt",
                List.of("spring_boot_unavailable", "search_recovery_used")
        );
        List<ProductCardResponse> cards = List.of(card("775"));

        when(aiServiceClient.chat(request)).thenReturn(aiResponse);
        when(productResolver.resolve(rankedResults)).thenReturn(cards);
        when(chatPersistenceService.recordChatTurn(request, aiResponse, cards)).thenReturn(Optional.of(12L));

        var response = service.chat(request);

        assertThat(response.products()).containsExactlyElementsOf(cards);
        assertThat(response.warnings()).containsExactly("search_recovery_used");
    }

    private static ProductCardResponse card(String productId) {
        return new ProductCardResponse(
                productId,
                null,
                "Product " + productId,
                null,
                null,
                null,
                null,
                null,
                "VND",
                0,
                false,
                null,
                List.of(),
                null,
                null
        );
    }
}
