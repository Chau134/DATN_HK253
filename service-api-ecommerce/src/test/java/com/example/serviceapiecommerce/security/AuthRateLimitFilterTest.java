package com.example.serviceapiecommerce.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class AuthRateLimitFilterTest {
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void rejectsAuthenticationRequestsOverTheLimitWith429AndRetryAfter() throws Exception {
        Clock clock = Clock.fixed(Instant.parse("2026-08-30T00:00:00Z"), ZoneOffset.UTC);
        AuthRateLimitFilter filter = new AuthRateLimitFilter(objectMapper, true, 2, 60, clock);

        assertThat(invoke(filter, "/api/auth/login").getStatus()).isEqualTo(200);
        assertThat(invoke(filter, "/api/auth/login").getStatus()).isEqualTo(200);

        MockHttpServletResponse rejected = invoke(filter, "/api/auth/login");
        JsonNode body = objectMapper.readTree(rejected.getContentAsString());
        assertThat(rejected.getStatus()).isEqualTo(429);
        assertThat(rejected.getHeader("Retry-After")).isEqualTo("60");
        assertThat(rejected.getHeader("X-RateLimit-Remaining")).isEqualTo("0");
        assertThat(body.get("error").asText()).isEqualTo("rate_limit_exceeded");
        assertThat(body.get("path").asText()).isEqualTo("/api/auth/login");
    }

    @Test
    void doesNotLimitUnrelatedEndpoints() throws Exception {
        AuthRateLimitFilter filter = new AuthRateLimitFilter(objectMapper, true, 1, 60);
        FilterChain chain = mock(FilterChain.class);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/products");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(request, response);
        assertThat(response.getStatus()).isEqualTo(200);
    }

    private MockHttpServletResponse invoke(AuthRateLimitFilter filter, String path) throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", path);
        request.setRemoteAddr("203.0.113.10");
        MockHttpServletResponse response = new MockHttpServletResponse();
        filter.doFilter(request, response, (ignoredRequest, ignoredResponse) -> { });
        return response;
    }
}
