package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.repository.ProductRepository;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;

@Service
public class AiProductCandidateFallbackService {
    private static final int DEFAULT_TOP_K = 10;
    private static final int MAX_TOP_K = 50;

    private final ProductRepository productRepository;

    public AiProductCandidateFallbackService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    public List<AiProductResultDto> keywordSearch(String query, Integer topK, String source) {
        if (!hasText(query)) {
            return List.of();
        }
        return searchByKeyword(query, limit(topK), source);
    }

    public List<AiProductResultDto> mockSearch(String query, Integer topK, String source) {
        int limit = limit(topK);
        List<AiProductResultDto> results = hasText(query)
                ? searchByKeyword(query, limit, source)
                : List.of();
        if (!results.isEmpty()) {
            return results;
        }
        return toResults(productRepository.findMockAiCandidates(PageRequest.of(0, limit)), source);
    }

    private List<AiProductResultDto> searchByKeyword(String query, int limit, String source) {
        Map<Long, Product> productsById = new LinkedHashMap<>();
        String normalizedQuery = normalize(query);
        collect(productsById, productRepository.findMockAiCandidatesByKeyword(
                normalizedQuery,
                PageRequest.of(0, limit)
        ));

        if (productsById.size() < limit) {
            for (String token : tokens(normalizedQuery)) {
                collect(productsById, productRepository.findMockAiCandidatesByKeyword(
                        token,
                        PageRequest.of(0, limit)
                ));
                if (productsById.size() >= limit) {
                    break;
                }
            }
        }

        return toResults(productsById.values().stream().limit(limit).toList(), source);
    }

    private static void collect(Map<Long, Product> productsById, List<Product> products) {
        for (Product product : products) {
            productsById.putIfAbsent(product.getId(), product);
        }
    }

    private static List<AiProductResultDto> toResults(Iterable<Product> products, String source) {
        List<AiProductResultDto> results = new ArrayList<>();
        int index = 0;
        for (Product product : products) {
            results.add(new AiProductResultDto(
                    String.valueOf(product.getId()),
                    Math.max(0.1, 1.0 - (index * 0.01)),
                    source
            ));
            index++;
        }
        return results;
    }

    private static List<String> tokens(String query) {
        return Arrays.stream(query.split("[\\s,.;:/_\\-]+"))
                .filter(token -> token.length() > 1)
                .toList();
    }

    private static String normalize(String value) {
        return value.trim().toLowerCase(Locale.ROOT);
    }

    private static int limit(Integer topK) {
        if (topK == null || topK <= 0) {
            return DEFAULT_TOP_K;
        }
        return Math.min(topK, MAX_TOP_K);
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
