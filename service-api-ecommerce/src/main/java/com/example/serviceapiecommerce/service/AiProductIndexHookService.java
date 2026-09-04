package com.example.serviceapiecommerce.service;

public interface AiProductIndexHookService {
    void syncProductAfterCommit(Long productId);

    void deleteProductAfterCommit(Long productId);
}
