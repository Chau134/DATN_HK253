package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.ExpectedCount.times;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;

import com.example.serviceapiecommerce.config.AiServiceProperties;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import com.example.serviceapiecommerce.observability.CorrelationId;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class RestAiServiceClientCorrelationTest {
    @Test
    void backgroundOperationKeepsOneCorrelationIdAcrossRetriesAndClearsMdc() {
        List<String> observedIds = new ArrayList<>();
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("http://ai.test")
                .requestInterceptor((request, body, execution) -> {
                    request.getHeaders().set(CorrelationId.HEADER_NAME, CorrelationId.currentOrCreate());
                    return execution.execute(request, body);
                });
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        RestAiServiceClient client = new RestAiServiceClient(properties(), builder.build());
        server.expect(times(3), requestTo("http://ai.test/search/text"))
                .andExpect(request -> observedIds.add(
                        request.getHeaders().getFirst(CorrelationId.HEADER_NAME)
                ))
                .andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE));

        client.textSearch(new AiTextSearchRequest("black hoodie", null, 5));

        assertThat(observedIds).hasSize(3).doesNotContainNull();
        assertThat(observedIds).allMatch(observedIds.getFirst()::equals);
        assertThat(MDC.get(CorrelationId.MDC_KEY)).isNull();
        server.verify();
    }

    private static AiServiceProperties properties() {
        return new AiServiceProperties(
                true,
                false,
                "http://ai.test",
                "secret",
                1,
                new AiServiceProperties.Sync(50, "0 */10 * * * *")
        );
    }
}
