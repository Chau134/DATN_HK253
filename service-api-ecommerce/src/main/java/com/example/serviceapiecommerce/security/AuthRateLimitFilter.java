package com.example.serviceapiecommerce.security;

import com.example.serviceapiecommerce.dto.error.ApiErrorResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Clock;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Per-client fixed-window protection for authentication endpoints.
 *
 * <p>The in-memory store is suitable for this application's single backend instance. When the
 * backend is scaled horizontally, replace it with a shared Redis-backed counter while preserving
 * the same HTTP contract.</p>
 */
public class AuthRateLimitFilter extends OncePerRequestFilter {
    private static final Set<String> PROTECTED_PATHS = Set.of(
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/refresh",
            "/api/auth/password-reset/request",
            "/api/auth/password-reset/verify",
            "/api/auth/password-reset/confirm"
    );
    private static final long CLEANUP_INTERVAL = 1_024;

    private final ObjectMapper objectMapper;
    private final boolean enabled;
    private final int maxRequests;
    private final long windowSeconds;
    private final Clock clock;
    private final ConcurrentHashMap<String, Window> windows = new ConcurrentHashMap<>();
    private final AtomicLong requestSequence = new AtomicLong();

    public AuthRateLimitFilter(
            ObjectMapper objectMapper,
            boolean enabled,
            int maxRequests,
            long windowSeconds
    ) {
        this(objectMapper, enabled, maxRequests, windowSeconds, Clock.systemUTC());
    }

    AuthRateLimitFilter(
            ObjectMapper objectMapper,
            boolean enabled,
            int maxRequests,
            long windowSeconds,
            Clock clock
    ) {
        if (maxRequests < 1 || windowSeconds < 1) {
            throw new IllegalArgumentException("Rate limit and window must be positive");
        }
        this.objectMapper = objectMapper;
        this.enabled = enabled;
        this.maxRequests = maxRequests;
        this.windowSeconds = windowSeconds;
        this.clock = clock;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !enabled
                || !HttpMethod.POST.matches(request.getMethod())
                || !PROTECTED_PATHS.contains(request.getRequestURI());
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        long now = clock.instant().getEpochSecond();
        Admission admission = admit(clientKey(request), now);

        response.setHeader("X-RateLimit-Limit", Integer.toString(maxRequests));
        response.setHeader("X-RateLimit-Remaining", Integer.toString(admission.remaining()));
        if (!admission.allowed()) {
            long retryAfter = Math.max(1, admission.resetAtEpochSecond() - now);
            response.setStatus(org.springframework.http.HttpStatus.TOO_MANY_REQUESTS.value());
            response.setHeader("Retry-After", Long.toString(retryAfter));
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            objectMapper.writeValue(response.getWriter(), ApiErrorResponse.of(
                    "rate_limit_exceeded",
                    "Too many authentication requests; retry later",
                    org.springframework.http.HttpStatus.TOO_MANY_REQUESTS.value(),
                    request.getRequestURI()
            ));
            return;
        }

        if (requestSequence.incrementAndGet() % CLEANUP_INTERVAL == 0) {
            windows.entrySet().removeIf(entry -> entry.getValue().resetAtEpochSecond() <= now);
        }
        filterChain.doFilter(request, response);
    }

    private Admission admit(String key, long now) {
        Window updated = windows.compute(key, (ignored, current) -> {
            if (current == null || current.resetAtEpochSecond() <= now) {
                return new Window(1, now + windowSeconds);
            }
            return new Window(current.count() + 1, current.resetAtEpochSecond());
        });
        boolean allowed = updated.count() <= maxRequests;
        int remaining = Math.max(0, maxRequests - updated.count());
        return new Admission(allowed, remaining, updated.resetAtEpochSecond());
    }

    private static String clientKey(HttpServletRequest request) {
        return request.getRemoteAddr();
    }

    private record Window(int count, long resetAtEpochSecond) {
    }

    private record Admission(boolean allowed, int remaining, long resetAtEpochSecond) {
    }
}
