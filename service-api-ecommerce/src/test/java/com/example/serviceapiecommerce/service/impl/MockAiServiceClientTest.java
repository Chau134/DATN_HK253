package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class MockAiServiceClientTest {
    @Mock
    private AiProductCandidateFallbackService candidateFallbackService;

    @Test
    void textSearchReturnsMockProductIdsFromDatabaseFallback() {
        MockAiServiceClient client = new MockAiServiceClient(candidateFallbackService);
        AiTextSearchRequest request = new AiTextSearchRequest("black hoodie", null, 2);
        List<AiProductResultDto> results = List.of(
                new AiProductResultDto("2", 1.0, "mock"),
                new AiProductResultDto("1", 0.99, "mock")
        );

        when(candidateFallbackService.mockSearch("black hoodie", 2, "mock")).thenReturn(results);

        var response = client.textSearch(request);

        assertThat(response.productIds()).containsExactly("2", "1");
        assertThat(response.results()).containsExactlyElementsOf(results);
        assertThat(response.warnings()).containsExactly("ai_service_mock_enabled");
    }

    @Test
    void autoSearchReturnsMockRoute() {
        MockAiServiceClient client = new MockAiServiceClient(candidateFallbackService);
        AiAutoSearchRequest request = new AiAutoSearchRequest("black hoodie", null, null, null, 2, "vi-VN");
        List<AiProductResultDto> results = List.of(new AiProductResultDto("2", 1.0, "mock"));

        when(candidateFallbackService.mockSearch("black hoodie", 2, "mock")).thenReturn(results);

        var response = client.autoSearch(request);

        assertThat(response.route()).isEqualTo("text_search");
        assertThat(response.productIds()).containsExactly("2");
    }

    @Test
    void chatReturnsFriendlyMockMessageAndProducts() {
        MockAiServiceClient client = new MockAiServiceClient(candidateFallbackService);
        AiChatRequest request = new AiChatRequest("session-1", "user-1", "find hoodie", null, null, "vi-VN");
        List<AiProductResultDto> results = List.of(new AiProductResultDto("2", 1.0, "mock"));

        when(candidateFallbackService.mockSearch("find hoodie", null, "mock")).thenReturn(results);

        var response = client.chat(request);

        assertThat(response.sessionId()).isEqualTo("session-1");
        assertThat(response.message()).contains("Mock assistant response");
        assertThat(response.productIds()).containsExactlyElementsOf(results);
        assertThat(response.warnings()).containsExactly("ai_service_mock_enabled");
    }
}
