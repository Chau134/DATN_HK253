package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.repository.ProductRepository;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageRequest;

@ExtendWith(MockitoExtension.class)
class AiProductCandidateFallbackServiceTest {
    @Mock
    private ProductRepository productRepository;

    @Test
    void keywordSearchReturnsRankedProductIdsFromDatabase() {
        AiProductCandidateFallbackService service = new AiProductCandidateFallbackService(productRepository);

        when(productRepository.findMockAiCandidatesByKeyword("black hoodie", PageRequest.of(0, 2)))
                .thenReturn(List.of(product(2L)));
        when(productRepository.findMockAiCandidatesByKeyword("black", PageRequest.of(0, 2)))
                .thenReturn(List.of(product(1L)));

        var results = service.keywordSearch("Black Hoodie", 2, "keyword_fallback");

        assertThat(results).extracting("productId").containsExactly("2", "1");
        assertThat(results).extracting("source").containsExactly("keyword_fallback", "keyword_fallback");
        assertThat(results.getFirst().score()).isEqualTo(1.0);
    }

    @Test
    void mockSearchBrowsesProductsWhenQueryDoesNotMatch() {
        AiProductCandidateFallbackService service = new AiProductCandidateFallbackService(productRepository);

        when(productRepository.findMockAiCandidatesByKeyword("unknown", PageRequest.of(0, 3))).thenReturn(List.of());
        when(productRepository.findMockAiCandidates(PageRequest.of(0, 3)))
                .thenReturn(List.of(product(3L), product(4L)));

        var results = service.mockSearch("unknown", 3, "mock");

        assertThat(results).extracting("productId").containsExactly("3", "4");
        assertThat(results).extracting("source").containsExactly("mock", "mock");
    }

    private static Product product(Long id) {
        Product product = new Product();
        product.setId(id);
        product.setProductDisplayName("Product " + id);
        return product;
    }
}
