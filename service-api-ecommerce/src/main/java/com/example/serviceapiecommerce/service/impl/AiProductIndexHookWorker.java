package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiIndexSingleResponse;
import com.example.serviceapiecommerce.service.AiProductSyncService;
import com.example.serviceapiecommerce.service.AiServiceClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Service
public class AiProductIndexHookWorker {
    private static final Logger log = LoggerFactory.getLogger(AiProductIndexHookWorker.class);

    private final AiProductSyncService syncService;
    private final AiServiceClient aiServiceClient;

    public AiProductIndexHookWorker(AiProductSyncService syncService, AiServiceClient aiServiceClient) {
        this.syncService = syncService;
        this.aiServiceClient = aiServiceClient;
    }

    @Async("aiIndexHookExecutor")
    public void syncProduct(Long productId) {
        try {
            AiIndexSingleResponse response = syncService.syncProduct(productId);
            if (response.failedCount() > 0 || !response.warnings().isEmpty()) {
                log.warn(
                        "ai_product_index_hook_sync_warning product_id={} failed_count={} warnings={}",
                        productId,
                        response.failedCount(),
                        response.warnings()
                );
            }
        } catch (RuntimeException ex) {
            log.warn(
                    "ai_product_index_hook_sync_failed product_id={} error_type={}",
                    productId,
                    ex.getClass().getSimpleName()
            );
        }
    }

    @Async("aiIndexHookExecutor")
    public void deleteProduct(Long productId) {
        try {
            aiServiceClient.deleteProduct(String.valueOf(productId));
        } catch (RuntimeException ex) {
            log.warn(
                    "ai_product_index_hook_delete_failed product_id={} error_type={}",
                    productId,
                    ex.getClass().getSimpleName()
            );
        }
    }
}
