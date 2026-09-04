package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiSyncResponse;
import com.example.serviceapiecommerce.repository.AiSyncJobRepository;
import com.example.serviceapiecommerce.service.AiProductSyncService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

@Component
public class AiSyncJobWorker {
    private static final Logger log = LoggerFactory.getLogger(AiSyncJobWorker.class);

    private final AiProductSyncService syncService;
    private final AiSyncJobRepository repository;
    private final ObjectMapper objectMapper;

    public AiSyncJobWorker(
            AiProductSyncService syncService,
            AiSyncJobRepository repository,
            ObjectMapper objectMapper
    ) {
        this.syncService = syncService;
        this.repository = repository;
        this.objectMapper = objectMapper;
    }

    @Async("aiSyncExecutor")
    public void runLimitedFullSync(String jobId, int limit) {
        repository.markRunning(jobId);
        try {
            AiSyncResponse response = syncService.runLimitedFullSync(limit);
            repository.markSucceeded(jobId, serialize(response));
        } catch (RuntimeException exception) {
            String error = exception.getClass().getSimpleName();
            repository.markFailed(jobId, error);
            log.error("ai_sync_job_failed job_id={} error_type={}", jobId, error);
        }
    }

    private String serialize(AiSyncResponse response) {
        try {
            return objectMapper.writeValueAsString(response);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Could not serialize AI sync result", exception);
        }
    }
}
