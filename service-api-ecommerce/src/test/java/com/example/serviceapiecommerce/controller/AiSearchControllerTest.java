package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiHybridSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionResponse;
import com.example.serviceapiecommerce.dto.ai.AiImageSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import com.example.serviceapiecommerce.dto.response.AiProductSearchResponse;
import com.example.serviceapiecommerce.service.AiProductSearchService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AiSearchControllerTest {
    @Mock
    private AiProductSearchService searchService;

    @Test
    void textSearchDelegatesToService() {
        AiSearchController controller = new AiSearchController(searchService);
        AiTextSearchRequest request = new AiTextSearchRequest("black hoodie", null, 10);
        AiProductSearchResponse expected = new AiProductSearchResponse("black hoodie", null, "text_search", List.of(), List.of(), List.of());

        when(searchService.textSearch(request)).thenReturn(expected);

        AiProductSearchResponse response = controller.textSearch(request);

        assertThat(response).isEqualTo(expected);
        verify(searchService).textSearch(request);
    }

    @Test
    void autoSearchDelegatesToService() {
        AiSearchController controller = new AiSearchController(searchService);
        AiAutoSearchRequest request = new AiAutoSearchRequest("black hoodie", null, null, null, 10, "vi-VN");
        AiProductSearchResponse expected = new AiProductSearchResponse("black hoodie", null, "text_search", List.of(), List.of(), List.of());

        when(searchService.autoSearch(request)).thenReturn(expected);

        AiProductSearchResponse response = controller.autoSearch(request);

        assertThat(response).isEqualTo(expected);
        verify(searchService).autoSearch(request);
    }

    @Test
    void hybridSearchDelegatesToService() {
        AiSearchController controller = new AiSearchController(searchService);
        AiHybridSearchRequest request = new AiHybridSearchRequest("black hoodie", null, null, null, 10, "weighted");
        AiProductSearchResponse expected = new AiProductSearchResponse("black hoodie", null, "hybrid_search", List.of(), List.of(), List.of());

        when(searchService.hybridSearch(request)).thenReturn(expected);

        AiProductSearchResponse response = controller.hybridSearch(request);

        assertThat(response).isEqualTo(expected);
        verify(searchService).hybridSearch(request);
    }

    @Test
    void imageSearchDelegatesToService() {
        AiSearchController controller = new AiSearchController(searchService);
        AiImageSearchRequest request = new AiImageSearchRequest(null, null, null, 10);
        AiProductSearchResponse expected = new AiProductSearchResponse(null, null, "image_search", List.of(), List.of(), List.of());

        when(searchService.imageSearch(request)).thenReturn(expected);

        AiProductSearchResponse response = controller.imageSearch(request);

        assertThat(response).isEqualTo(expected);
        verify(searchService).imageSearch(request);
    }

    @Test
    void detectImageDelegatesToService() {
        AiSearchController controller = new AiSearchController(searchService);
        AiImageDetectionRequest request = new AiImageDetectionRequest(null);
        AiImageDetectionResponse expected = new AiImageDetectionResponse(100, 80, List.of(), List.of());

        when(searchService.detectImage(request)).thenReturn(expected);

        AiImageDetectionResponse response = controller.detectImage(request);

        assertThat(response).isEqualTo(expected);
        verify(searchService).detectImage(request);
    }
}
