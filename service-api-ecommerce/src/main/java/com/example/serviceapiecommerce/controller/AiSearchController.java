package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiHybridSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionResponse;
import com.example.serviceapiecommerce.dto.ai.AiImageSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import com.example.serviceapiecommerce.dto.response.AiProductSearchResponse;
import com.example.serviceapiecommerce.service.AiProductSearchService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/search/ai")
public class AiSearchController {
    private final AiProductSearchService searchService;

    public AiSearchController(AiProductSearchService searchService) {
        this.searchService = searchService;
    }

    @PostMapping("/text")
    public AiProductSearchResponse textSearch(@Valid @RequestBody AiTextSearchRequest request) {
        return searchService.textSearch(request);
    }

    @PostMapping("/auto")
    public AiProductSearchResponse autoSearch(@Valid @RequestBody AiAutoSearchRequest request) {
        return searchService.autoSearch(request);
    }

    @PostMapping("/image")
    public AiProductSearchResponse imageSearch(@Valid @RequestBody AiImageSearchRequest request) {
        return searchService.imageSearch(request);
    }

    @PostMapping("/image/detections")
    public AiImageDetectionResponse detectImage(@Valid @RequestBody AiImageDetectionRequest request) {
        return searchService.detectImage(request);
    }

    @PostMapping("/hybrid")
    public AiProductSearchResponse hybridSearch(@Valid @RequestBody AiHybridSearchRequest request) {
        return searchService.hybridSearch(request);
    }
}
