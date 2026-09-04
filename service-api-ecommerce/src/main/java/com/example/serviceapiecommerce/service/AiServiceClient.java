package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatResponse;
import com.example.serviceapiecommerce.dto.ai.AiAutoSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiHybridSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionRequest;
import com.example.serviceapiecommerce.dto.ai.AiImageDetectionResponse;
import com.example.serviceapiecommerce.dto.ai.AiImageSearchRequest;
import com.example.serviceapiecommerce.dto.ai.AiIndexBatchResponse;
import com.example.serviceapiecommerce.dto.ai.AiIndexSingleResponse;
import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import com.example.serviceapiecommerce.dto.ai.AiSearchResponse;
import com.example.serviceapiecommerce.dto.ai.AiTextSearchRequest;
import java.util.List;

public interface AiServiceClient {
    AiIndexBatchResponse indexProducts(List<AiProductIndexItemDto> items);

    AiIndexSingleResponse indexProduct(AiProductIndexItemDto item);

    void deleteProduct(String productId);

    AiSearchResponse textSearch(AiTextSearchRequest request);

    AiSearchResponse autoSearch(AiAutoSearchRequest request);

    AiSearchResponse imageSearch(AiImageSearchRequest request);

    AiImageDetectionResponse detectImage(AiImageDetectionRequest request);

    AiSearchResponse hybridSearch(AiHybridSearchRequest request);

    AiChatResponse chat(AiChatRequest request);
}
