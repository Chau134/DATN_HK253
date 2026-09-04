package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiHybridSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionResponse;
import com.example.serviceapiecommerce.dto.ai.AiImageSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.ai.AiSearchFilterDto;
import com.example.serviceapiecommerce.dto.ai.AiSearchResponse;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import com.example.serviceapiecommerce.dto.response.AiProductSearchResponse;
import com.example.serviceapiecommerce.dto.response.ProductCardResponse;
import com.example.serviceapiecommerce.service.AiProductResolver;
import com.example.serviceapiecommerce.service.AiProductSearchService;
import com.example.serviceapiecommerce.service.AiServiceClient;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class AiProductSearchServiceImpl implements AiProductSearchService {
    private static final String WARNING_DISABLED = "ai_service_disabled";
    private static final String WARNING_KEYWORD_FALLBACK = "ai_keyword_fallback";
    private static final String WARNING_MOCK = "ai_service_mock_enabled";
    private static final String WARNING_UNAVAILABLE = "ai_service_unavailable";
    private static final String SOURCE_KEYWORD_FALLBACK = "keyword_fallback";

    private final AiServiceClient aiServiceClient;
    private final AiProductResolver productResolver;
    private final AiProductCandidateFallbackService candidateFallbackService;
    private final Counter keywordFallbackCounter;

    public AiProductSearchServiceImpl(
            AiServiceClient aiServiceClient,
            AiProductResolver productResolver,
            AiProductCandidateFallbackService candidateFallbackService,
            MeterRegistry meterRegistry
    ) {
        this.aiServiceClient = aiServiceClient;
        this.productResolver = productResolver;
        this.candidateFallbackService = candidateFallbackService;
        this.keywordFallbackCounter = Counter.builder("ecommerce.ai.search.fallback")
                .description("AI product-search fallbacks by decision")
                .tag("decision", "keyword")
                .register(meterRegistry);
    }

    @Override
    public AiProductSearchResponse textSearch(AiTextSearchRequest request) {
        AiSearchResponse aiResponse = aiServiceClient.textSearch(request);
        return resolve(
                aiResponse,
                request == null ? null : request.query(),
                request == null ? null : request.topK(),
                request == null ? null : request.filters()
        );
    }

    @Override
    public AiProductSearchResponse autoSearch(AiAutoSearchRequest request) {
        AiSearchResponse aiResponse = aiServiceClient.autoSearch(request);
        return resolve(
                aiResponse,
                request == null ? null : request.query(),
                request == null ? null : request.topK(),
                request == null ? null : request.filters()
        );
    }

    @Override
    public AiProductSearchResponse imageSearch(AiImageSearchRequest request) {
        AiSearchResponse aiResponse = aiServiceClient.imageSearch(request);
        return resolve(
                aiResponse,
                null,
                request == null ? null : request.topK(),
                request == null ? null : request.filters()
        );
    }

    @Override
    public AiImageDetectionResponse detectImage(AiImageDetectionRequest request) {
        return aiServiceClient.detectImage(request);
    }

    @Override
    public AiProductSearchResponse hybridSearch(AiHybridSearchRequest request) {
        AiSearchResponse aiResponse = aiServiceClient.hybridSearch(request);
        return resolve(
                aiResponse,
                request == null ? null : request.query(),
                request == null ? null : request.topK(),
                request == null ? null : request.filters()
        );
    }

    private AiProductSearchResponse resolve(
            AiSearchResponse aiResponse,
            String fallbackQuery,
            Integer topK,
            AiSearchFilterDto requestFilters
    ) {
        if (aiResponse == null) {
            aiResponse = AiSearchResponse.unavailable(fallbackQuery, requestFilters, WARNING_UNAVAILABLE);
        }
        List<AiProductResultDto> rankedResults = rankedResults(aiResponse);
        List<String> warnings = aiResponse.warnings();

        if (rankedResults.isEmpty() && shouldUseKeywordFallback(aiResponse, fallbackQuery)) {
            List<AiProductResultDto> fallbackResults = candidateFallbackService.keywordSearch(
                    fallbackQuery,
                    topK,
                    SOURCE_KEYWORD_FALLBACK
            );
            if (!fallbackResults.isEmpty()) {
                rankedResults = fallbackResults;
                warnings = appendWarning(warnings, WARNING_KEYWORD_FALLBACK);
                keywordFallbackCounter.increment();
            }
        }

        List<ProductCardResponse> products = rankedResults.isEmpty()
                ? List.of()
                : productResolver.resolve(rankedResults);
        return new AiProductSearchResponse(
                aiResponse.rewrittenQuery(),
                aiResponse.filters(),
                aiResponse.route(),
                products,
                aiResponse.detections(),
                warnings
        );
    }

    private static List<AiProductResultDto> rankedResults(AiSearchResponse aiResponse) {
        if (!aiResponse.results().isEmpty()) {
            return aiResponse.results();
        }
        return aiResponse.productIds().stream()
                .map(productId -> new AiProductResultDto(productId, null, null))
                .toList();
    }

    private static boolean shouldUseKeywordFallback(AiSearchResponse aiResponse, String fallbackQuery) {
        return hasText(fallbackQuery) && aiResponse.warnings().stream().anyMatch(AiProductSearchServiceImpl::isAiFailureWarning);
    }

    private static boolean isAiFailureWarning(String warning) {
        return WARNING_DISABLED.equals(warning)
                || WARNING_MOCK.equals(warning)
                || WARNING_UNAVAILABLE.equals(warning);
    }

    private static List<String> appendWarning(List<String> warnings, String warning) {
        if (warnings.contains(warning)) {
            return warnings;
        }
        ArrayList<String> updated = new ArrayList<>(warnings);
        updated.add(warning);
        return List.copyOf(updated);
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
