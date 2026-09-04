package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatExceptionOfType;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.config.AiServiceProperties;
import com.example.serviceapiecommerce.dto.ai.AiProductContextRequest;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductDetailResponse;
import com.example.serviceapiecommerce.service.CatalogService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class InternalAiProductControllerTest {
    @Mock
    private CatalogService catalogService;

    @Test
    void productContextAuthenticatesDeduplicatesAndDelegatesAsOneBatch() {
        InternalAiProductController controller = controller();
        List<CatalogProductDetailResponse> expected = List.of();
        when(catalogService.getProductsByIds(List.of(2L, 1L))).thenReturn(expected);

        List<CatalogProductDetailResponse> result = controller.productContext(
                "secret",
                new AiProductContextRequest(List.of("2", "1", "2"))
        );

        assertThat(result).isSameAs(expected);
        verify(catalogService).getProductsByIds(List.of(2L, 1L));
    }

    @Test
    void productContextRejectsInvalidApiKeyBeforeCatalogAccess() {
        InternalAiProductController controller = controller();

        assertThatExceptionOfType(ResponseStatusException.class)
                .isThrownBy(() -> controller.productContext(
                        "wrong",
                        new AiProductContextRequest(List.of("1"))
                ))
                .satisfies(exception -> assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED));
        verifyNoInteractions(catalogService);
    }

    @Test
    void productContextRejectsNonNumericProductId() {
        InternalAiProductController controller = controller();

        assertThatExceptionOfType(ResponseStatusException.class)
                .isThrownBy(() -> controller.productContext(
                        "secret",
                        new AiProductContextRequest(List.of("not-a-number"))
                ))
                .satisfies(exception -> assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST));
        verifyNoInteractions(catalogService);
    }

    private InternalAiProductController controller() {
        AiServiceProperties properties = new AiServiceProperties(
                true,
                false,
                "http://ai.test",
                "secret",
                30,
                new AiServiceProperties.Sync(50, "0 */10 * * * *")
        );
        return new InternalAiProductController(catalogService, properties);
    }
}
