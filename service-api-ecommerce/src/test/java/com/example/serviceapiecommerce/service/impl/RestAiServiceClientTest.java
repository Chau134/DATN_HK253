package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.ExpectedCount.times;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.example.serviceapiecommerce.config.AiServiceProperties;
import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatResponse;
import com.example.serviceapiecommerce.dto.ai.AiIndexBatchResponse;
import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import com.example.serviceapiecommerce.dto.ai.AiSearchResponse;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class RestAiServiceClientTest {
    @Test
    void textSearchSendsInternalApiKeyAndParsesResponse() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("http://ai.test")
                .defaultHeader("X-Internal-API-Key", "secret");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        RestAiServiceClient client = new RestAiServiceClient(properties(true, false), builder.build());

        server.expect(requestTo("http://ai.test/search/text"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Internal-API-Key", "secret"))
                .andRespond(withSuccess(
                        """
                                {
                                  "rewritten_query": "black hoodie",
                                  "filters": null,
                                  "product_ids": ["42"],
                                  "results": [{"product_id": "42", "score": 0.91, "source": "text"}]
                                }
                                """,
                        MediaType.APPLICATION_JSON
                ));

        AiSearchResponse response = client.textSearch(new AiTextSearchRequest("black hoodie", null, 5));

        assertThat(response.productIds()).containsExactly("42");
        assertThat(response.results()).hasSize(1);
        assertThat(response.warnings()).isEmpty();
        server.verify();
    }

    @Test
    void autoSearchSendsInternalApiKeyAndParsesRoute() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("http://ai.test")
                .defaultHeader("X-Internal-API-Key", "secret");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        RestAiServiceClient client = new RestAiServiceClient(properties(true, false), builder.build());

        server.expect(requestTo("http://ai.test/search/auto"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Internal-API-Key", "secret"))
                .andRespond(withSuccess(
                        """
                                {
                                  "rewritten_query": "black hoodie",
                                  "filters": null,
                                  "route": "text_search",
                                  "product_ids": ["42"],
                                  "results": [{"product_id": "42", "score": 0.91, "source": "text"}]
                                }
                                """,
                        MediaType.APPLICATION_JSON
                ));

        AiSearchResponse response = client.autoSearch(new AiAutoSearchRequest("black hoodie", null, null, null, 5, "vi-VN"));

        assertThat(response.route()).isEqualTo("text_search");
        assertThat(response.productIds()).containsExactly("42");
        server.verify();
    }

    @Test
    void chatSendsInternalApiKeyAndParsesResponse() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("http://ai.test")
                .defaultHeader("X-Internal-API-Key", "secret");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        RestAiServiceClient client = new RestAiServiceClient(properties(true, false), builder.build());
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

        server.expect(requestTo("http://ai.test/assistant/chat"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Internal-API-Key", "secret"))
                .andExpect(jsonPath("$.request_id").value("request-1"))
                .andExpect(jsonPath("$.turn_sequence").value(1))
                .andRespond(withSuccess(
                        """
                                {
                                  "session_id": "session-1",
                                  "message": "Here are some options.",
                                  "product_ids": [
                                    {"product_id": "42", "score": 0.91, "source": "hybrid"}
                                  ],
                                  "rewritten_query": "black hoodie",
                                  "warnings": []
                                }
                                """,
                        MediaType.APPLICATION_JSON
                ));

        AiChatResponse response = client.chat(request);

        assertThat(response.sessionId()).isEqualTo("session-1");
        assertThat(response.message()).isEqualTo("Here are some options.");
        assertThat(response.productIds()).hasSize(1);
        assertThat(response.productIds().getFirst().productId()).isEqualTo("42");
        assertThat(response.warnings()).isEmpty();
        server.verify();
    }

    @Test
    void retriesTransientFailuresAndReturnsControlledFallback() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("http://ai.test")
                .defaultHeader("X-Internal-API-Key", "secret");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        RestAiServiceClient client = new RestAiServiceClient(properties(true, false), builder.build());

        server.expect(times(3), requestTo("http://ai.test/search/text"))
                .andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE));

        AiSearchResponse response = client.textSearch(new AiTextSearchRequest("black hoodie", null, 5));

        assertThat(response.productIds()).isEmpty();
        assertThat(response.results()).isEmpty();
        assertThat(response.warnings()).containsExactly("ai_service_unavailable");
        server.verify();
    }

    @Test
    void indexProductsDoesNotRetryMutatingRequest() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("http://ai.test")
                .defaultHeader("X-Internal-API-Key", "secret");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        RestAiServiceClient client = new RestAiServiceClient(properties(true, false), builder.build());

        server.expect(times(1), requestTo("http://ai.test/internal/index/products/batch"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE));

        AiIndexBatchResponse response = client.indexProducts(List.<AiProductIndexItemDto>of());

        assertThat(response.warnings()).containsExactly("ai_service_unavailable");
        server.verify();
    }

    @Test
    void disabledClientReturnsFallbackWithoutCallingPython() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://ai.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        RestAiServiceClient client = new RestAiServiceClient(properties(false, false), builder.build());

        AiSearchResponse response = client.textSearch(new AiTextSearchRequest("black hoodie", null, 5));

        assertThat(response.productIds()).isEmpty();
        assertThat(response.warnings()).containsExactly("ai_service_disabled");
        server.verify();
    }

    private static AiServiceProperties properties(boolean enabled, boolean mock) {
        return new AiServiceProperties(
                enabled,
                mock,
                "http://ai.test",
                "secret",
                1,
                new AiServiceProperties.Sync(50, "0 */10 * * * *")
        );
    }
}
