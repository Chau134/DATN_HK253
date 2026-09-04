package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiHybridSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionResponse;
import com.example.serviceapiecommerce.dto.ai.AiImageSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import com.example.serviceapiecommerce.dto.response.AiProductSearchResponse;

public interface AiProductSearchService {
    AiProductSearchResponse textSearch(AiTextSearchRequest request);

    AiProductSearchResponse autoSearch(AiAutoSearchRequest request);

    AiProductSearchResponse imageSearch(AiImageSearchRequest request);

    AiImageDetectionResponse detectImage(AiImageDetectionRequest request);

    AiProductSearchResponse hybridSearch(AiHybridSearchRequest request);
}
