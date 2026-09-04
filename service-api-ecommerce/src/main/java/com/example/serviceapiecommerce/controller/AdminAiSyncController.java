package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.ai.AiIndexSingleResponse;
import com.example.serviceapiecommerce.dto.ai.AiSyncJobResponse;
import com.example.serviceapiecommerce.dto.ai.AiSyncResponse;
import com.example.serviceapiecommerce.service.AiSyncJobService;
import com.example.serviceapiecommerce.service.AiProductSyncService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/ai-sync")
public class AdminAiSyncController {
    private final AiProductSyncService syncService;
    private final AiSyncJobService syncJobService;

    public AdminAiSyncController(AiProductSyncService syncService, AiSyncJobService syncJobService) {
        this.syncService = syncService;
        this.syncJobService = syncJobService;
    }

    @PostMapping("/full")
    public AiSyncResponse runFullSync() {
        return syncService.runFullSync();
    }

    @PostMapping("/limit")
    public AiSyncResponse runLimitedFullSync(@RequestParam(defaultValue = "100") int limit) {
        return syncService.runLimitedFullSync(limit);
    }

    @PostMapping("/jobs/limit")
    public ResponseEntity<AiSyncJobResponse> submitLimitedFullSyncJob(
            @RequestParam(defaultValue = "100") int limit
    ) {
        return ResponseEntity.accepted().body(syncJobService.submitLimitedFullSync(limit));
    }

    @GetMapping("/jobs/{jobId}")
    public AiSyncJobResponse getSyncJob(@PathVariable String jobId) {
        return syncJobService.getJob(jobId);
    }

    @PostMapping("/incremental")
    public AiSyncResponse runIncrementalSync() {
        return syncService.runIncrementalSync();
    }

    @PostMapping("/products/{productId}")
    public AiIndexSingleResponse syncProduct(@PathVariable Long productId) {
        return syncService.syncProduct(productId);
    }

    @PostMapping("/test-embedding/products/{productId}")
    public AiIndexSingleResponse testProductEmbedding(@PathVariable Long productId) {
        return syncService.syncProduct(productId);
    }
}
