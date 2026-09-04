package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.config.AiServiceProperties;
import com.example.serviceapiecommerce.dto.ai.AiProductContextRequest;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductDetailResponse;
import com.example.serviceapiecommerce.service.CatalogService;
import jakarta.validation.Valid;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/internal/ai/products")
public class InternalAiProductController {
    private final CatalogService catalogService;
    private final AiServiceProperties aiServiceProperties;

    public InternalAiProductController(CatalogService catalogService, AiServiceProperties aiServiceProperties) {
        this.catalogService = catalogService;
        this.aiServiceProperties = aiServiceProperties;
    }

    @PostMapping("/context")
    public List<CatalogProductDetailResponse> productContext(
            @RequestHeader(name = "X-API-Key", required = false) String apiKey,
            @Valid @RequestBody AiProductContextRequest request
    ) {
        requireValidApiKey(apiKey);
        List<Long> productIds = request.productIds().stream()
                .map(InternalAiProductController::parseProductId)
                .distinct()
                .toList();
        return catalogService.getProductsByIds(productIds);
    }

    private void requireValidApiKey(String apiKey) {
        String expected = aiServiceProperties.internalApiKey();
        if (apiKey == null || expected == null || !MessageDigest.isEqual(
                apiKey.getBytes(StandardCharsets.UTF_8),
                expected.getBytes(StandardCharsets.UTF_8)
        )) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "invalid_internal_api_key");
        }
    }

    private static Long parseProductId(String rawProductId) {
        try {
            return Long.valueOf(rawProductId.trim());
        } catch (NumberFormatException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_product_id");
        }
    }
}
