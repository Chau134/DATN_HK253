package com.example.serviceapiecommerce.controller;

import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
@ConditionalOnProperty(name = "app.oauth2.google.enabled", havingValue = "false", matchIfMissing = true)
public class OAuth2UnavailableController {
    private final String failureRedirectUri;

    public OAuth2UnavailableController(
            @Value("${app.oauth2.failure-redirect-uri:http://localhost:5173/login?oauth2_error=google_login_failed}")
            String failureRedirectUri
    ) {
        this.failureRedirectUri = failureRedirectUri;
    }

    @GetMapping("/oauth2/authorization/google")
    public void redirectWhenGoogleOAuthDisabled(HttpServletResponse response) throws IOException {
        response.sendRedirect(failureRedirect("google_oauth_not_configured"));
    }

    private String failureRedirect(String error) {
        String uri = removeQueryParam(stripFragment(failureRedirectUri), "oauth2_error");
        String separator = uri.contains("?") ? "&" : "?";
        return uri + separator + "oauth2_error=" + encode(error);
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
}
