package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatResponse;
import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiHybridSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionBoxDto;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionResponse;
import com.example.serviceapiecommerce.dto.ai.AiImageSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiIndexBatchResponse;
import com.example.serviceapiecommerce.dto.ai.AiIndexSingleResponse;
import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.ai.AiSearchResponse;
import com.example.serviceapiecommerce.dto.ai.AiSearchFilterDto;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import com.example.serviceapiecommerce.service.AiServiceClient;
import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

@Service
@ConditionalOnProperty(prefix = "ai.service", name = "mock", havingValue = "true")
public class MockAiServiceClient implements AiServiceClient {
    private static final String WARNING_MOCK = "ai_service_mock_enabled";
    private static final String SOURCE_MOCK = "mock";

    private final AiProductCandidateFallbackService candidateFallbackService;

    public MockAiServiceClient(AiProductCandidateFallbackService candidateFallbackService) {
        this.candidateFallbackService = candidateFallbackService;
    }

    @Override
    public AiIndexBatchResponse indexProducts(List<AiProductIndexItemDto> items) {
        int indexedCount = items == null ? 0 : items.size();
        return new AiIndexBatchResponse(indexedCount, 0, 0, 0, List.of(), List.of(WARNING_MOCK));
    }

    @Override
    public AiIndexSingleResponse indexProduct(AiProductIndexItemDto item) {
        return new AiIndexSingleResponse(
                item == null ? null : item.productId(),
                item == null ? 0 : 1,
                0,
                0,
                0,
                List.of(),
                List.of(WARNING_MOCK)
        );
    }

    @Override
    public void deleteProduct(String productId) {
        // Mock mode intentionally does not mutate an AI index.
    }

    @Override
    public AiSearchResponse textSearch(AiTextSearchRequest request) {
        List<AiProductResultDto> results = candidateFallbackService.mockSearch(
                request == null ? null : request.query(),
                request == null ? null : request.topK(),
                SOURCE_MOCK
        );
        return searchResponse(
                request == null ? null : request.query(),
                request == null ? null : request.filters(),
                "text_search",
                results,
                List.of()
        );
    }

    @Override
    public AiSearchResponse autoSearch(AiAutoSearchRequest request) {
        List<AiProductResultDto> results = candidateFallbackService.mockSearch(
                request == null ? null : request.query(),
                request == null ? null : request.topK(),
                SOURCE_MOCK
        );
        String route = request != null && request.image() != null
                ? (request.query() == null || request.query().isBlank() ? "image_search" : "hybrid_search")
                : "text_search";
        return searchResponse(
                request == null ? null : request.query(),
                request == null ? null : request.filters(),
                route,
                results,
                List.of()
        );
    }

    @Override
    public AiSearchResponse imageSearch(AiImageSearchRequest request) {
        List<AiProductResultDto> results = candidateFallbackService.mockSearch(
                null,
                request == null ? null : request.topK(),
                SOURCE_MOCK
        );
        return searchResponse(
                null,
                request == null ? null : request.filters(),
                "image_search",
                results,
                List.of()
        );
    }

    @Override
    public AiImageDetectionResponse detectImage(AiImageDetectionRequest request) {
        return new AiImageDetectionResponse(null, null, List.of(), List.of(WARNING_MOCK));
    }

    @Override
    public AiSearchResponse hybridSearch(AiHybridSearchRequest request) {
        List<AiProductResultDto> results = candidateFallbackService.mockSearch(
                request == null ? null : request.query(),
                request == null ? null : request.topK(),
                SOURCE_MOCK
        );
        return searchResponse(
                request == null ? null : request.query(),
                request == null ? null : request.filters(),
                "hybrid_search",
                results,
                List.of()
        );
    }

    @Override
    public AiChatResponse chat(AiChatRequest request) {
        List<AiProductResultDto> results = candidateFallbackService.mockSearch(
                request == null ? null : request.message(),
                null,
                SOURCE_MOCK
        );
        return new AiChatResponse(
                request == null ? null : request.sessionId(),
                "Mock assistant response. Python AI service is not running.",
                results,
                null,
                request == null ? null : request.message(),
                List.of(WARNING_MOCK)
        );
    }

    private static AiSearchResponse searchResponse(
            String rewrittenQuery,
            AiSearchFilterDto filters,
            String route,
            List<AiProductResultDto> results,
            List<AiImageDetectionBoxDto> detections
    ) {
        return new AiSearchResponse(
                rewrittenQuery,
                filters,
                route,
                results.stream().map(AiProductResultDto::productId).toList(),
                results,
                detections,
                List.of(WARNING_MOCK)
        );
    }
}
