package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.dto.ai.AiIndexSingleResponse;
import com.example.serviceapiecommerce.dto.ai.AiSyncResponse;
import com.example.serviceapiecommerce.service.AiProductSyncService;
import com.example.serviceapiecommerce.service.AiSyncJobService;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AdminAiSyncControllerTest {
    @Mock
    private AiProductSyncService syncService;
    @Mock
    private AiSyncJobService syncJobService;

    @Test
    void testProductEmbeddingDelegatesToManualProductSync() {
        AdminAiSyncController controller = new AdminAiSyncController(syncService, syncJobService);
        AiIndexSingleResponse expected = new AiIndexSingleResponse("42", 1, 0, 0, 0, List.of(), List.of());

        when(syncService.syncProduct(42L)).thenReturn(expected);

        AiIndexSingleResponse response = controller.testProductEmbedding(42L);

        assertThat(response).isEqualTo(expected);
        verify(syncService).syncProduct(42L);
    }

    @Test
    void limitedFullSyncDelegatesToServiceWithLimit() {
        AdminAiSyncController controller = new AdminAiSyncController(syncService, syncJobService);
        AiSyncResponse expected = new AiSyncResponse(
                "product_index",
                "limited_full",
                100L,
                100L,
                0L,
                10,
                0L,
                0L,
                List.of(),
                List.of(),
                Instant.parse("2026-05-14T09:00:00Z"),
                null
        );

        when(syncService.runLimitedFullSync(100)).thenReturn(expected);

        AiSyncResponse response = controller.runLimitedFullSync(100);

        assertThat(response).isEqualTo(expected);
        verify(syncService).runLimitedFullSync(100);
    }
}
