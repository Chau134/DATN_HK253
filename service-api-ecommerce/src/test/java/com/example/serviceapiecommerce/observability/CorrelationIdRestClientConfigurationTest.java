package com.example.serviceapiecommerce.observability;

import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class CorrelationIdRestClientConfigurationTest {
    @Test
    void propagatesMdcCorrelationIdOnOutboundRequest() {
        RestClient.Builder builder = RestClient.builder();
        new CorrelationIdRestClientConfiguration().correlationIdRestClientCustomizer().customize(builder);
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        RestClient client = builder.baseUrl("http://ai.test").build();
        MDC.put(CorrelationId.MDC_KEY, "backend-request-42");
        try {
            server.expect(requestTo("http://ai.test/health"))
                    .andExpect(header(CorrelationId.HEADER_NAME, "backend-request-42"))
                    .andRespond(withSuccess());

            client.get().uri("/health").retrieve().toBodilessEntity();
        } finally {
            MDC.remove(CorrelationId.MDC_KEY);
        }
        server.verify();
    }
}
