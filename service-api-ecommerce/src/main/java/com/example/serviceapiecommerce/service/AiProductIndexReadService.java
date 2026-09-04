package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import java.time.Instant;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

public interface AiProductIndexReadService {
    AiProductIndexItemDto getProductForAiIndex(Long productId);

    Page<AiProductIndexItemDto> getProductsForFullSync(Pageable pageable);

    Page<AiProductIndexItemDto> getProductsUpdatedAfter(Instant updatedAfter, Pageable pageable);
}
