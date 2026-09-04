package com.example.serviceapiecommerce.security;

import com.example.serviceapiecommerce.dto.error.ApiErrorResponse;
import com.example.serviceapiecommerce.observability.CorrelationId;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

@Configuration
public class SecurityConfig {
    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final GoogleOAuth2AuthenticationSuccessHandler googleOAuth2SuccessHandler;
    private final ObjectMapper objectMapper;
    private final String allowedOrigins;
    private final boolean googleOAuthEnabled;
    private final String oauthFailureRedirectUri;

    public SecurityConfig(
            JwtAuthenticationFilter jwtAuthenticationFilter,
            GoogleOAuth2AuthenticationSuccessHandler googleOAuth2SuccessHandler,
            ObjectMapper objectMapper,
            @Value("${app.cors.allowed-origins:http://localhost:5173,http://127.0.0.1:5173}") String allowedOrigins,
            @Value("${app.oauth2.google.enabled:false}") boolean googleOAuthEnabled,
            @Value("${app.oauth2.failure-redirect-uri:http://localhost:5173/login?oauth2_error=google_login_failed}")
            String oauthFailureRedirectUri
    ) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
        this.googleOAuth2SuccessHandler = googleOAuth2SuccessHandler;
        this.objectMapper = objectMapper;
        this.allowedOrigins = allowedOrigins;
        this.googleOAuthEnabled = googleOAuthEnabled;
        this.oauthFailureRedirectUri = oauthFailureRedirectUri;
    }

    @Bean
    SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            AuthRateLimitFilter authRateLimitFilter
    ) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(
                        googleOAuthEnabled ? SessionCreationPolicy.IF_REQUIRED : SessionCreationPolicy.STATELESS
                ))
                .authorizeHttpRequests(authorize -> authorize
                        .requestMatchers(
                                HttpMethod.POST,
                                "/api/auth/register",
                                "/api/auth/login",
                                "/api/auth/refresh",
                                "/api/auth/password-reset/request",
                                "/api/auth/password-reset/verify",
                                "/api/auth/password-reset/confirm"
                        )
                        .permitAll()
                        .requestMatchers("/oauth2/**", "/login/oauth2/**")
                        .permitAll()
                        .requestMatchers("/v3/api-docs/**", "/swagger-ui.html", "/swagger-ui/**")
                        .permitAll()
                        .requestMatchers("/api/search/ai/**", "/api/assistant/**")
                        .permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/payments/webhooks/**")
                        .permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/reviews/recent")
                        .permitAll()
                        .requestMatchers(
                                "/api/auth/logout",
                                "/api/me",
                                "/api/me/**",
                                "/api/cart",
                                "/api/cart/**",
                                "/api/checkout",
                                "/api/checkout/**",
                                "/api/orders",
                                "/api/orders/**",
                                "/api/payments",
                                "/api/payments/**",
                                "/api/coupons",
                                "/api/coupons/**",
                                "/api/reviews",
                                "/api/reviews/**",
                                "/api/wishlists",
                                "/api/wishlists/**"
                        )
                        .authenticated()
                        .requestMatchers("/admin/**")
                        .hasRole("ADMIN")
                        .anyRequest()
                        .permitAll()
                )
                .exceptionHandling(exception -> exception
                        .authenticationEntryPoint((request, response, authException) -> {
                            response.setStatus(401);
                            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
                            objectMapper.writeValue(response.getWriter(), ApiErrorResponse.of(
                                    "unauthorized",
                                    "Authentication is required",
                                    401,
                                    request.getRequestURI()
                            ));
                        })
                        .accessDeniedHandler((request, response, accessDeniedException) -> {
                            response.setStatus(403);
                            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
                            objectMapper.writeValue(response.getWriter(), ApiErrorResponse.of(
                                    "forbidden",
                                    "Access is denied",
                                    403,
                                    request.getRequestURI()
                            ));
                        })
                )
                .httpBasic(httpBasic -> httpBasic.disable())
                .formLogin(formLogin -> formLogin.disable())
                .cors(Customizer.withDefaults())
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class)
                .addFilterBefore(authRateLimitFilter, JwtAuthenticationFilter.class);

        if (googleOAuthEnabled) {
            http.oauth2Login(oauth2 -> oauth2
                    .successHandler(googleOAuth2SuccessHandler)
                    .failureUrl(oauthFailureRedirectUri)
            );
        }

        return http.build();
    }

    @Bean
    AuthRateLimitFilter authRateLimitFilter(
            @Value("${app.security.rate-limit.auth.enabled:true}") boolean enabled,
            @Value("${app.security.rate-limit.auth.max-requests:10}") int maxRequests,
            @Value("${app.security.rate-limit.auth.window-seconds:60}") long windowSeconds
    ) {
        return new AuthRateLimitFilter(objectMapper, enabled, maxRequests, windowSeconds);
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(splitCsv(allowedOrigins));
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of(
                "Authorization", "Content-Type", "X-Requested-With", CorrelationId.HEADER_NAME
        ));
        configuration.setExposedHeaders(List.of("Location", CorrelationId.HEADER_NAME));
        configuration.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    private static List<String> splitCsv(String value) {
        return Arrays.stream(value.split(","))
                .map(String::trim)
                .filter(item -> !item.isBlank())
                .toList();
    }
}
