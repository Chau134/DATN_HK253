package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.config.AiServiceProperties;
import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatResponse;
import com.example.serviceapiecommerce.dto.ai.AiHybridSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionResponse;
import com.example.serviceapiecommerce.dto.ai.AiImageSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiIndexBatchResponse;
import com.example.serviceapiecommerce.dto.ai.AiIndexSingleResponse;
import com.example.serviceapiecommerce.dto.ai.AiProductIndexBatchRequest;
import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import com.example.serviceapiecommerce.dto.ai.AiSearchResponse;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import com.example.serviceapiecommerce.observability.CorrelationId;
import com.example.serviceapiecommerce.service.AiServiceClient;
import java.time.Duration;
import java.util.List;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Service
@ConditionalOnProperty(prefix = "ai.service", name = "mock", havingValue = "false", matchIfMissing = true)
public class RestAiServiceClient implements AiServiceClient {
    private static final Logger log = LoggerFactory.getLogger(RestAiServiceClient.class);
    private static final String INTERNAL_API_KEY_HEADER = "X-Internal-API-Key";
    private static final int MAX_ATTEMPTS = 3;
    private static final long INITIAL_RETRY_DELAY_MILLIS = 200L;
    private static final String WARNING_DISABLED = "ai_service_disabled";
    private static final String WARNING_MOCK = "ai_service_mock_enabled";
    private static final String WARNING_UNAVAILABLE = "ai_service_unavailable";

    private final AiServiceProperties properties;
    private final RestClient restClient;

    @Autowired
    public RestAiServiceClient(AiServiceProperties properties, RestClient.Builder restClientBuilder) {
        this(properties, buildRestClient(properties, restClientBuilder));
    }

    RestAiServiceClient(AiServiceProperties properties, RestClient restClient) {
        this.properties = properties;
        this.restClient = restClient;
    }

    @Override
    public AiIndexBatchResponse indexProducts(List<AiProductIndexItemDto> items) {
        int itemCount = items == null ? 0 : items.size();
        return executeNoRetry(
                "index_products_batch",
                () -> restClient.post()
                        .uri("/internal/index/products/batch")
                        .body(new AiProductIndexBatchRequest(items == null ? List.of() : items))
                        .retrieve()
                        .body(AiIndexBatchResponse.class),
                warning -> AiIndexBatchResponse.unavailable(itemCount, warning)
        );
    }

    @Override
    public AiIndexSingleResponse indexProduct(AiProductIndexItemDto item) {
        String productId = item == null ? null : item.productId();
        return executeNoRetry(
                "index_product",
                () -> {
                    AiIndexBatchResponse response = restClient.post()
                            .uri("/internal/index/products/{product_id}", productId)
                            .body(item)
                            .retrieve()
                            .body(AiIndexBatchResponse.class);
                    if (response == null) {
                        return AiIndexSingleResponse.unavailable(productId, WARNING_UNAVAILABLE);
                    }
                    return AiIndexSingleResponse.fromBatch(productId, response);
                },
                warning -> AiIndexSingleResponse.unavailable(productId, warning)
        );
    }

    @Override
    public void deleteProduct(String productId) {
        if (shouldShortCircuit()) {
            log.warn("ai_delete_product_skipped product_id={} warning={}", productId, shortCircuitWarning());
            return;
        }
        executeVoidNoRetry(
                "delete_product",
                () -> restClient.delete()
                        .uri("/internal/index/products/{product_id}", productId)
                        .retrieve()
                        .toBodilessEntity()
        );
    }

    @Override
    public AiSearchResponse textSearch(AiTextSearchRequest request) {
        return execute(
                "text_search",
                () -> restClient.post()
                        .uri("/search/text")
                        .body(request)
                        .retrieve()
                        .body(AiSearchResponse.class),
                warning -> AiSearchResponse.unavailable(
                        request == null ? null : request.query(),
                        request == null ? null : request.filters(),
                        warning
                )
        );
    }

    @Override
    public AiSearchResponse autoSearch(AiAutoSearchRequest request) {
        return execute(
                "auto_search",
                () -> restClient.post()
                        .uri("/search/auto")
                        .body(request)
                        .retrieve()
                        .body(AiSearchResponse.class),
                warning -> AiSearchResponse.unavailable(
                        request == null ? null : request.query(),
                        request == null ? null : request.filters(),
                        warning
                )
        );
    }

    @Override
    public AiSearchResponse imageSearch(AiImageSearchRequest request) {
        return execute(
                "image_search",
                () -> restClient.post()
                        .uri("/search/image")
                        .body(request)
                        .retrieve()
                        .body(AiSearchResponse.class),
                warning -> AiSearchResponse.unavailable(
                        null,
                        request == null ? null : request.filters(),
                        warning
                )
        );
    }

    @Override
    public AiImageDetectionResponse detectImage(AiImageDetectionRequest request) {
        return execute(
                "image_detection",
                () -> restClient.post()
                        .uri("/search/image/detections")
                        .body(request)
                        .retrieve()
                        .body(AiImageDetectionResponse.class),
                AiImageDetectionResponse::unavailable
        );
    }

    @Override
    public AiSearchResponse hybridSearch(AiHybridSearchRequest request) {
        return execute(
                "hybrid_search",
                () -> restClient.post()
                        .uri("/search/hybrid")
                        .body(request)
                        .retrieve()
                        .body(AiSearchResponse.class),
                warning -> AiSearchResponse.unavailable(
                        request == null ? null : request.query(),
                        request == null ? null : request.filters(),
                        warning
                )
        );
    }

    @Override
    public AiChatResponse chat(AiChatRequest request) {
        return execute(
                "chat",
                () -> restClient.post()
                        .uri("/assistant/chat")
                        .body(request)
                        .retrieve()
                        .body(AiChatResponse.class),
                warning -> AiChatResponse.unavailable(request, warning)
        );
    }

    private <T> T execute(String operation, Supplier<T> request, FunctionWithWarning<T> fallback) {
        return execute(operation, request, fallback, MAX_ATTEMPTS);
    }

    private <T> T executeNoRetry(String operation, Supplier<T> request, FunctionWithWarning<T> fallback) {
        return execute(operation, request, fallback, 1);
    }

    private <T> T execute(
            String operation,
            Supplier<T> request,
            FunctionWithWarning<T> fallback,
            int maxAttempts
    ) {
        boolean ownsCorrelationId = CorrelationId.ensureBound();
        try {
            return executeCorrelated(operation, request, fallback, maxAttempts);
        } finally {
            if (ownsCorrelationId) {
                CorrelationId.clear();
            }
        }
    }

    private <T> T executeCorrelated(
            String operation,
            Supplier<T> request,
            FunctionWithWarning<T> fallback,
            int maxAttempts
    ) {
        if (shouldShortCircuit()) {
            return fallback.apply(shortCircuitWarning());
        }

        RestClientException lastException = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                T response = request.get();
                if (response != null) {
                    return response;
                }
                return fallback.apply(WARNING_UNAVAILABLE);
            } catch (RestClientResponseException ex) {
                lastException = ex;
                if (!isTransientStatus(ex.getStatusCode()) || attempt == maxAttempts) {
                    break;
                }
                sleepBeforeRetry(operation, attempt, ex);
            } catch (RestClientException ex) {
                lastException = ex;
                if (attempt == maxAttempts) {
                    break;
                }
                sleepBeforeRetry(operation, attempt, ex);
            }
        }

        log.warn(
                "ai_service_request_failed operation={} warning={} error_type={}",
                operation,
                WARNING_UNAVAILABLE,
                lastException == null ? "unknown" : lastException.getClass().getSimpleName()
        );
        return fallback.apply(WARNING_UNAVAILABLE);
    }

    private void executeVoidNoRetry(String operation, Runnable request) {
        executeNoRetry(operation, () -> {
            request.run();
            return Boolean.TRUE;
        }, warning -> {
            log.warn("ai_service_void_request_fallback operation={} warning={}", operation, warning);
            return Boolean.FALSE;
        });
    }

    private boolean shouldShortCircuit() {
        return !properties.enabled() || properties.mock();
    }

    private String shortCircuitWarning() {
        if (!properties.enabled()) {
            return WARNING_DISABLED;
        }
        if (properties.mock()) {
            return WARNING_MOCK;
        }
        return WARNING_UNAVAILABLE;
    }

    private static RestClient buildRestClient(AiServiceProperties properties, RestClient.Builder builder) {
        Duration timeout = Duration.ofSeconds(properties.timeoutSeconds());
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(timeout);
        requestFactory.setReadTimeout(timeout);

        return builder
                .baseUrl(properties.baseUrl())
                .defaultHeader(INTERNAL_API_KEY_HEADER, properties.internalApiKey())
                .requestFactory(requestFactory)
                .build();
    }

    private static boolean isTransientStatus(HttpStatusCode statusCode) {
        int status = statusCode.value();
        return status == 408 || status == 425 || status == 429 || status >= 500;
    }

    private static void sleepBeforeRetry(String operation, int attempt, RestClientException exception) {
        long delayMillis = INITIAL_RETRY_DELAY_MILLIS * (1L << Math.max(attempt - 1, 0));
        log.warn(
                "ai_service_request_retrying operation={} attempt={} delay_ms={} error_type={}",
                operation,
                attempt,
                delayMillis,
                exception.getClass().getSimpleName()
        );
        try {
            Thread.sleep(delayMillis);
        } catch (InterruptedException interruptedException) {
            Thread.currentThread().interrupt();
        }
    }

    @FunctionalInterface
    private interface FunctionWithWarning<T> {
        T apply(String warning);
    }
}
