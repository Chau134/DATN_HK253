package com.example.serviceapiecommerce.security;

import com.example.serviceapiecommerce.dto.auth.AuthTokenResponse;
import com.example.serviceapiecommerce.service.AuthService;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import java.util.stream.Collectors;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
public class GoogleOAuth2AuthenticationSuccessHandler implements AuthenticationSuccessHandler {
    private static final Logger log = LoggerFactory.getLogger(GoogleOAuth2AuthenticationSuccessHandler.class);

    private final ObjectProvider<AuthService> authServiceProvider;
    private final ObjectMapper objectMapper;
    private final String successRedirectUri;
    private final String failureRedirectUri;

    public GoogleOAuth2AuthenticationSuccessHandler(
            ObjectProvider<AuthService> authServiceProvider,
            ObjectMapper objectMapper,
            @Value("${app.oauth2.authorized-redirect-uri:http://localhost:5173/oauth2/callback}")
            String successRedirectUri,
            @Value("${app.oauth2.failure-redirect-uri:http://localhost:5173/login?oauth2_error=google_login_failed}")
            String failureRedirectUri
    ) {
        this.authServiceProvider = authServiceProvider;
        this.objectMapper = objectMapper;
        this.successRedirectUri = successRedirectUri;
        this.failureRedirectUri = failureRedirectUri;
    }

    @Override
    public void onAuthenticationSuccess(
            HttpServletRequest request,
            HttpServletResponse response,
            Authentication authentication
    ) throws IOException, ServletException {
        if (!(authentication.getPrincipal() instanceof OAuth2User oauth2User)) {
            response.sendRedirect(failureRedirect("invalid_oauth2_principal"));
            return;
        }

        String email = stringAttribute(oauth2User, "email");
        Object emailVerified = oauth2User.getAttribute("email_verified");
        if (email == null || email.isBlank() || Boolean.FALSE.equals(emailVerified)) {
            response.sendRedirect(failureRedirect("google_email_not_verified"));
            return;
        }

        try {
            AuthTokenResponse tokenResponse = authServiceProvider.getObject().loginWithGoogleOAuth(
                    email,
                    stringAttribute(oauth2User, "name"),
                    stringAttribute(oauth2User, "picture"),
                    clientIp(request),
                    request.getHeader("User-Agent")
            );
            response.sendRedirect(successRedirect(tokenResponse));
        } catch (ResponseStatusException exception) {
            String reason = exception.getReason() == null ? "google_login_failed" : exception.getReason();
            log.warn(
                    "google_oauth_login_failed reason={} status={}",
                    reason,
                    exception.getStatusCode().value(),
                    exception
            );
            response.sendRedirect(failureRedirect(reason));
        } catch (Exception exception) {
            log.error("google_oauth_login_failed reason=unexpected", exception);
            response.sendRedirect(failureRedirect("google_login_failed"));
        }
    }

    private String successRedirect(AuthTokenResponse response) throws IOException {
        String userJson = Base64.getUrlEncoder()
                .withoutPadding()
                .encodeToString(objectMapper.writeValueAsBytes(response.user()));
        String fragment = "access_token=" + encode(response.accessToken())
                + "&refresh_token=" + encode(response.refreshToken())
                + "&token_type=" + encode(response.tokenType())
                + "&expires_in=" + response.expiresIn()
                + "&user=" + encode(userJson);
        return stripFragment(successRedirectUri) + "#" + fragment;
    }

    private String failureRedirect(String error) {
        String uri = removeQueryParam(stripFragment(failureRedirectUri), "oauth2_error");
        String separator = uri.contains("?") ? "&" : "?";
        return uri + separator + "oauth2_error=" + encode(error);
    }

    private static String stringAttribute(OAuth2User user, String name) {
        Object value = user.getAttribute(name);
        return value == null ? null : value.toString();
    }

    private static String encode(String value) {
        return URLEncoder.encode(value == null ? "" : value, StandardCharsets.UTF_8);
    }

    private static String stripFragment(String uri) {
        int fragmentIndex = uri.indexOf('#');
        return fragmentIndex >= 0 ? uri.substring(0, fragmentIndex) : uri;
    }

    private static String removeQueryParam(String uri, String name) {
        int queryIndex = uri.indexOf('?');
        if (queryIndex < 0) {
            return uri;
        }

        String baseUri = uri.substring(0, queryIndex);
        String query = uri.substring(queryIndex + 1);
        String filteredQuery = Arrays.stream(query.split("&"))
                .filter(param -> !param.equals(name) && !param.startsWith(name + "="))
                .collect(Collectors.joining("&"));
        return filteredQuery.isBlank() ? baseUri : baseUri + "?" + filteredQuery;
    }

    private static String clientIp(HttpServletRequest request) {
        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (forwardedFor != null && !forwardedFor.isBlank()) {
            return forwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
