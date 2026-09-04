package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.ai.AiIndexSingleResponse;
import com.example.serviceapiecommerce.dto.ai.AiSyncResponse;

public interface AiProductSyncService {
    AiSyncResponse runFullSync();

    AiSyncResponse runLimitedFullSync(int limit);

    AiSyncResponse runIncrementalSync();

    AiIndexSingleResponse syncProduct(Long productId);
}
