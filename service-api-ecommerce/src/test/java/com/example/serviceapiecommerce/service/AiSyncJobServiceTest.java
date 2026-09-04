package com.example.serviceapiecommerce.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.repository.AiSyncJobRepository;
import com.example.serviceapiecommerce.repository.AiSyncJobRepository.AiSyncJobRecord;
import com.example.serviceapiecommerce.service.impl.AiSyncJobWorker;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class AiSyncJobServiceTest {
    @Mock
    private AiSyncJobRepository repository;
    @Mock
    private AiSyncJobWorker worker;

    private AiSyncJobService service;

    @BeforeEach
    void setUp() {
        service = new AiSyncJobService(repository, worker, new ObjectMapper());
    }

    @Test
    void submitCreatesQueuedJobAndDispatchesWorker() {
        ArgumentCaptor<String> jobId = ArgumentCaptor.forClass(String.class);
        Instant createdAt = Instant.parse("2026-07-16T08:00:00Z");
        when(repository.findById(org.mockito.ArgumentMatchers.anyString()))
                .thenAnswer(invocation -> Optional.of(new AiSyncJobRecord(
                        invocation.getArgument(0),
                        "limited_full",
                        500,
                        "QUEUED",
                        null,
                        null,
                        createdAt,
                        null,
                        null
                )));

        var response = service.submitLimitedFullSync(500);

        verify(repository).create(jobId.capture(), org.mockito.ArgumentMatchers.eq("limited_full"),
                org.mockito.ArgumentMatchers.eq(500));
        verify(worker).runLimitedFullSync(jobId.getValue(), 500);
        assertThat(response.jobId()).isEqualTo(jobId.getValue());
        assertThat(response.status()).isEqualTo("QUEUED");
    }

    @Test
    void submitRejectsWhenAnotherJobIsActive() {
        when(repository.hasActiveJob("limited_full")).thenReturn(true);

        assertThatThrownBy(() -> service.submitLimitedFullSync(500))
                .isInstanceOfSatisfying(ResponseStatusException.class, exception ->
                        assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.CONFLICT));
    }

    @Test
    void submitRejectsUnsafeLimit() {
        assertThatThrownBy(() -> service.submitLimitedFullSync(0))
                .isInstanceOfSatisfying(ResponseStatusException.class, exception ->
                        assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST));
    }

    @Test
    void submitMarksJobFailedWhenQueueIsFull() {
        doThrow(new TaskRejectedException("full"))
                .when(worker)
                .runLimitedFullSync(org.mockito.ArgumentMatchers.anyString(), org.mockito.ArgumentMatchers.eq(500));

        assertThatThrownBy(() -> service.submitLimitedFullSync(500))
                .isInstanceOfSatisfying(ResponseStatusException.class, exception ->
                        assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE));
        verify(repository).markFailed(org.mockito.ArgumentMatchers.anyString(), org.mockito.ArgumentMatchers.eq("sync_queue_full"));
    }

    @Test
    void getJobReturnsNotFound() {
        when(repository.findById("missing")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.getJob("missing"))
                .isInstanceOfSatisfying(ResponseStatusException.class, exception ->
                        assertThat(exception.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND));
    }
}
