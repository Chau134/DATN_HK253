package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.service.AiProductIndexHookService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Service
public class AiProductIndexHookServiceImpl implements AiProductIndexHookService {
    private final AiProductIndexHookWorker worker;

    public AiProductIndexHookServiceImpl(AiProductIndexHookWorker worker) {
        this.worker = worker;
    }

    @Override
    public void syncProductAfterCommit(Long productId) {
        if (productId == null) {
            return;
        }
        runAfterCommit(() -> worker.syncProduct(productId));
    }

    @Override
    public void deleteProductAfterCommit(Long productId) {
        if (productId == null) {
            return;
        }
        runAfterCommit(() -> worker.deleteProduct(productId));
    }

    private static void runAfterCommit(Runnable task) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            task.run();
            return;
        }

        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                task.run();
            }
        });
    }
}
