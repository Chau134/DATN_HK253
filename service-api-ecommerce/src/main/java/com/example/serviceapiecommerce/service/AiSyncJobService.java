package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.ai.AiSyncJobResponse;
import com.example.serviceapiecommerce.dto.ai.AiSyncResponse;
import com.example.serviceapiecommerce.repository.AiSyncJobRepository;
import com.example.serviceapiecommerce.service.impl.AiSyncJobWorker;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.UUID;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AiSyncJobService {
    private static final String LIMITED_FULL_SYNC = "limited_full";
    private static final int MAX_LIMIT = 5_000;

    private final AiSyncJobRepository repository;
    private final AiSyncJobWorker worker;
    private final ObjectMapper objectMapper;

    public AiSyncJobService(
            AiSyncJobRepository repository,
            AiSyncJobWorker worker,
            ObjectMapper objectMapper
    ) {
        this.repository = repository;
        this.worker = worker;
        this.objectMapper = objectMapper;
    }

    public synchronized AiSyncJobResponse submitLimitedFullSync(int limit) {
        if (limit < 1 || limit > MAX_LIMIT) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "limit must be between 1 and " + MAX_LIMIT
            );
        }
        if (repository.hasActiveJob(LIMITED_FULL_SYNC)) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "An AI sync job is already queued or running"
            );
        }
        String jobId = UUID.randomUUID().toString();
        repository.create(jobId, LIMITED_FULL_SYNC, limit);
        try {
            worker.runLimitedFullSync(jobId, limit);
        } catch (TaskRejectedException exception) {
            repository.markFailed(jobId, "sync_queue_full");
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "AI sync queue is full",
                    exception
            );
        }
        return getJob(jobId);
    }

    public AiSyncJobResponse getJob(String jobId) {
        AiSyncJobRepository.AiSyncJobRecord record = repository.findById(jobId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND,
                        "AI sync job not found"
                ));
        return new AiSyncJobResponse(
                record.jobId(),
                record.status(),
                record.requestedLimit(),
                parseResult(record.resultJson()),
                record.errorMessage(),
                record.createdAt(),
                record.startedAt(),
                record.completedAt()
        );
    }

    private AiSyncResponse parseResult(String resultJson) {
        if (resultJson == null || resultJson.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(resultJson, AiSyncResponse.class);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("Could not parse AI sync job result", exception);
        }
    }
}
