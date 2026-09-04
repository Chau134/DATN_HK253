package com.example.serviceapiecommerce.service.impl;

import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@ExtendWith(MockitoExtension.class)
class AiProductIndexHookServiceImplTest {
    @Mock
    private AiProductIndexHookWorker worker;

    @AfterEach
    void clearSynchronization() {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void syncProductRunsImmediatelyWhenNoTransactionIsActive() {
        AiProductIndexHookServiceImpl service = new AiProductIndexHookServiceImpl(worker);

        service.syncProductAfterCommit(42L);

        verify(worker).syncProduct(42L);
    }

    @Test
    void syncProductWaitsForTransactionCommitWhenSynchronizationIsActive() {
        AiProductIndexHookServiceImpl service = new AiProductIndexHookServiceImpl(worker);
        TransactionSynchronizationManager.initSynchronization();

        service.syncProductAfterCommit(42L);

        verify(worker, never()).syncProduct(42L);

        TransactionSynchronizationManager.getSynchronizations()
                .forEach(synchronization -> synchronization.afterCommit());

        verify(worker).syncProduct(42L);
    }

    @Test
    void deleteProductWaitsForTransactionCommitWhenSynchronizationIsActive() {
        AiProductIndexHookServiceImpl service = new AiProductIndexHookServiceImpl(worker);
        TransactionSynchronizationManager.initSynchronization();

        service.deleteProductAfterCommit(42L);

        verify(worker, never()).deleteProduct(42L);

        TransactionSynchronizationManager.getSynchronizations()
                .forEach(synchronization -> synchronization.afterCommit());

        verify(worker).deleteProduct(42L);
    }
}
