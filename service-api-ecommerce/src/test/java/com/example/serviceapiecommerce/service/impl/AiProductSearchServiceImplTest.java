package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.ai.AiSearchResponse;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import com.example.serviceapiecommerce.dto.response.ProductCardResponse;
import com.example.serviceapiecommerce.service.AiProductResolver;
import com.example.serviceapiecommerce.service.AiServiceClient;
import java.util.List;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AiProductSearchServiceImplTest {
    @Mock
    private AiServiceClient aiServiceClient;

    @Mock
    private AiProductResolver productResolver;

    @Mock
    private AiProductCandidateFallbackService candidateFallbackService;

    @Test
    void textSearchCallsPythonAndResolvesRankedProducts() {
        AiProductSearchServiceImpl service = service();
        AiTextSearchRequest request = new AiTextSearchRequest("black hoodie", null, 2);
        List<AiProductResultDto> rankedResults = List.of(
                new AiProductResultDto("2", 0.91, "text"),
                new AiProductResultDto("1", 0.84, "text")
        );
        AiSearchResponse aiResponse = new AiSearchResponse(
                "rewritten black hoodie",
                null,
                "text_search",
                List.of("2", "1"),
                rankedResults,
                List.of(),
                List.of("low_confidence")
        );
        List<ProductCardResponse> cards = List.of(card("2"), card("1"));

        when(aiServiceClient.textSearch(request)).thenReturn(aiResponse);
        when(productResolver.resolve(rankedResults)).thenReturn(cards);

        var response = service.textSearch(request);

        assertThat(response.rewrittenQuery()).isEqualTo("rewritten black hoodie");
        assertThat(response.route()).isEqualTo("text_search");
        assertThat(response.products()).containsExactlyElementsOf(cards);
        assertThat(response.warnings()).containsExactly("low_confidence");
        verify(productResolver).resolve(rankedResults);
    }

    @Test
    void textSearchFallsBackToProductIdsWhenPythonOmitsResultObjects() {
        AiProductSearchServiceImpl service = service();
        AiTextSearchRequest request = new AiTextSearchRequest("black hoodie", null, 2);
        AiSearchResponse aiResponse = new AiSearchResponse(
                "black hoodie",
                null,
                "text_search",
                List.of("2", "1"),
                List.of(),
                List.of(),
                List.of()
        );

        when(aiServiceClient.textSearch(request)).thenReturn(aiResponse);
        when(productResolver.resolve(List.of(
                new AiProductResultDto("2", null, null),
                new AiProductResultDto("1", null, null)
        ))).thenReturn(List.of(card("2"), card("1")));

        var response = service.textSearch(request);

        assertThat(response.products()).extracting(ProductCardResponse::productId).containsExactly("2", "1");
    }

    @Test
    void autoSearchCallsPythonAndPreservesRoute() {
        AiProductSearchServiceImpl service = service();
        AiAutoSearchRequest request = new AiAutoSearchRequest("black hoodie", null, null, null, 2, "vi-VN");
        List<AiProductResultDto> rankedResults = List.of(new AiProductResultDto("2", 0.91, "text"));
        AiSearchResponse aiResponse = new AiSearchResponse(
                "rewritten black hoodie",
                null,
                "text_search",
                List.of("2"),
                rankedResults,
                List.of(),
                List.of()
        );
        List<ProductCardResponse> cards = List.of(card("2"));

        when(aiServiceClient.autoSearch(request)).thenReturn(aiResponse);
        when(productResolver.resolve(rankedResults)).thenReturn(cards);

        var response = service.autoSearch(request);

        assertThat(response.route()).isEqualTo("text_search");
        assertThat(response.products()).containsExactlyElementsOf(cards);
    }

    @Test
    void textSearchUsesKeywordFallbackWhenPythonIsUnavailable() {
        AiProductSearchServiceImpl service = service();
        AiTextSearchRequest request = new AiTextSearchRequest("black hoodie", null, 2);
        List<AiProductResultDto> fallbackResults = List.of(
                new AiProductResultDto("10", 1.0, "keyword_fallback"),
                new AiProductResultDto("11", 0.99, "keyword_fallback")
        );
        List<ProductCardResponse> cards = List.of(card("10"), card("11"));

        when(aiServiceClient.textSearch(request))
                .thenReturn(AiSearchResponse.unavailable("black hoodie", null, "ai_service_unavailable"));
        when(candidateFallbackService.keywordSearch("black hoodie", 2, "keyword_fallback"))
                .thenReturn(fallbackResults);
        when(productResolver.resolve(fallbackResults)).thenReturn(cards);

        var response = service.textSearch(request);

        assertThat(response.products()).extracting(ProductCardResponse::productId).containsExactly("10", "11");
        assertThat(response.warnings()).containsExactly("ai_service_unavailable", "ai_keyword_fallback");
    }

    private AiProductSearchServiceImpl service() {
        return new AiProductSearchServiceImpl(
                aiServiceClient,
                productResolver,
                candidateFallbackService,
                new SimpleMeterRegistry()
        );
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
