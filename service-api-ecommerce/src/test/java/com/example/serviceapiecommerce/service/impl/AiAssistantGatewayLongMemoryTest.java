package com.example.serviceapiecommerce.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.ExpectedCount.times;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.config.AiServiceProperties;
import com.example.serviceapiecommerce.controller.AiAssistantController;
import com.example.serviceapiecommerce.observability.CorrelationId;
import com.example.serviceapiecommerce.observability.CorrelationIdFilter;
import com.example.serviceapiecommerce.service.AiProductResolver;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.mock.http.client.MockClientHttpRequest;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.web.method.annotation.AuthenticationPrincipalArgumentResolver;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.client.RestClient;

class AiAssistantGatewayLongMemoryTest {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Test
    void longSessionPreservesMemoryIsolationOrderingAndReplayThroughGateway() throws Exception {
        List<ForwardedTurn> forwardedTurns = new ArrayList<>();
        Map<String, List<String>> sessionMessages = new LinkedHashMap<>();
        Map<String, String> responseByRequestId = new HashMap<>();

        RestClient.Builder builder = RestClient.builder()
                .baseUrl("http://ai.test")
                .defaultHeader("X-Internal-API-Key", "secret")
                .requestInterceptor((request, body, execution) -> {
                    request.getHeaders().set(CorrelationId.HEADER_NAME, CorrelationId.currentOrCreate());
                    return execution.execute(request, body);
                });
        MockRestServiceServer aiServer = MockRestServiceServer.bindTo(builder).build();
        aiServer.expect(times(10), requestTo("http://ai.test/assistant/chat"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Internal-API-Key", "secret"))
                .andExpect(header(CorrelationId.HEADER_NAME, org.hamcrest.Matchers.notNullValue()))
                .andRespond(request -> {
                    byte[] requestBody = ((MockClientHttpRequest) request).getBodyAsBytes();
                    JsonNode payload = OBJECT_MAPPER.readTree(requestBody);
                    ForwardedTurn turn = new ForwardedTurn(
                            payload.path("session_id").asText(),
                            payload.path("user_id").asText(),
                            payload.path("request_id").asText(),
                            payload.path("turn_sequence").asInt(),
                            payload.path("message").asText()
                    );
                    forwardedTurns.add(turn);

                    String responseBody = responseByRequestId.get(turn.requestId());
                    if (responseBody == null) {
                        List<String> remembered = sessionMessages.computeIfAbsent(
                                turn.sessionId(),
                                ignored -> new ArrayList<>()
                        );
                        remembered.add(turn.message());
                        responseBody = aiResponse(turn.sessionId(), "memory:" + String.join("|", remembered));
                        responseByRequestId.put(turn.requestId(), responseBody);
                    }
                    return withSuccess(responseBody, MediaType.APPLICATION_JSON).createResponse(request);
                });

        RestAiServiceClient aiClient = new RestAiServiceClient(properties(), builder.build());
        AiProductResolver productResolver = org.mockito.Mockito.mock(AiProductResolver.class);
        AiChatPersistenceService persistenceService = org.mockito.Mockito.mock(AiChatPersistenceService.class);
        AiAssistantChatServiceImpl gatewayService = new AiAssistantChatServiceImpl(
                aiClient,
                productResolver,
                persistenceService
        );
        MockMvc gateway = MockMvcBuilders
                .standaloneSetup(new AiAssistantController(gatewayService))
                .setCustomArgumentResolvers(new AuthenticationPrincipalArgumentResolver())
                .addFilters(new CorrelationIdFilter())
                .build();

        JsonNode firstA = chat(gateway, "session-a", "browser-a", "a-1", 1, "A-FIRST-blue");
        JsonNode firstB = chat(gateway, "session-b", "browser-b", "b-1", 1, "B-FIRST-red");
        for (int sequence = 2; sequence <= 6; sequence++) {
            chat(gateway, "session-a", "browser-a", "a-" + sequence, sequence, "A-MIDDLE-" + sequence);
        }
        JsonNode finalA = chat(gateway, "session-a", "browser-a", "a-7", 7, "A-LAST-size-L");
        JsonNode finalB = chat(gateway, "session-b", "browser-b", "b-2", 2, "B-LAST-size-S");
        JsonNode replayA = chat(gateway, "session-a", "browser-a", "a-7", 7, "A-LAST-size-L");

        assertThat(firstA.path("message").asText()).contains("A-FIRST-blue").doesNotContain("B-FIRST-red");
        assertThat(firstB.path("message").asText()).contains("B-FIRST-red").doesNotContain("A-FIRST-blue");
        assertThat(finalA.path("message").asText())
                .contains("A-FIRST-blue", "A-MIDDLE-6", "A-LAST-size-L")
                .doesNotContain("B-FIRST-red", "B-LAST-size-S");
        assertThat(finalB.path("message").asText())
                .contains("B-FIRST-red", "B-LAST-size-S")
                .doesNotContain("A-FIRST-blue", "A-LAST-size-L");
        assertThat(replayA).isEqualTo(finalA);

        List<ForwardedTurn> sessionATurns = forwardedTurns.stream()
                .filter(turn -> turn.sessionId().equals("session-a"))
                .toList();
        assertThat(sessionATurns).extracting(ForwardedTurn::turnSequence)
                .containsExactly(1, 2, 3, 4, 5, 6, 7, 7);
        assertThat(sessionATurns).extracting(ForwardedTurn::requestId)
                .containsExactly("a-1", "a-2", "a-3", "a-4", "a-5", "a-6", "a-7", "a-7");
        assertThat(sessionATurns).allMatch(turn -> turn.userId().equals("guest:browser-a"));
        assertThat(forwardedTurns.stream().filter(turn -> turn.sessionId().equals("session-b")).toList())
                .extracting(ForwardedTurn::turnSequence)
                .containsExactly(1, 2);
        assertThat(sessionMessages.get("session-a")).hasSize(7);
        assertThat(sessionMessages.get("session-b")).hasSize(2);
        aiServer.verify();
    }

    private static JsonNode chat(
            MockMvc gateway,
            String sessionId,
            String userId,
            String requestId,
            int turnSequence,
            String message
    ) throws Exception {
        ObjectNode request = OBJECT_MAPPER.createObjectNode();
        request.put("session_id", sessionId);
        request.put("user_id", userId);
        request.put("request_id", requestId);
        request.put("turn_sequence", turnSequence);
        request.put("message", message);
        request.put("locale", "vi-VN");
        String response = gateway.perform(post("/api/assistant/chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(OBJECT_MAPPER.writeValueAsBytes(request)))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString(StandardCharsets.UTF_8);
        return OBJECT_MAPPER.readTree(response);
    }

    private static String aiResponse(String sessionId, String message) throws JsonProcessingException {
        ObjectNode response = OBJECT_MAPPER.createObjectNode();
        response.put("session_id", sessionId);
        response.put("message", message);
        response.set("product_ids", emptyArray());
        response.set("warnings", emptyArray());
        return OBJECT_MAPPER.writeValueAsString(response);
    }

    private static ArrayNode emptyArray() {
        return OBJECT_MAPPER.createArrayNode();
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

    private record ForwardedTurn(
            String sessionId,
            String userId,
            String requestId,
            int turnSequence,
            String message
    ) {
    }
}
