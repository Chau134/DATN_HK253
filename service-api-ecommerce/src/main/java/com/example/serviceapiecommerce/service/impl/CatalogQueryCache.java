package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.catalog.CatalogPageResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductListItemResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductSearchRequest;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.LongSupplier;
import java.util.function.Supplier;
import org.springframework.stereotype.Component;

@Component
final class CatalogQueryCache {
    static final int MAX_ENTRIES = 256;
    static final Duration TTL = Duration.ofSeconds(2);

    private final Map<CatalogProductSearchRequest, CacheEntry> entries = new ConcurrentHashMap<>();
    private final LongSupplier ticker;

    CatalogQueryCache() {
        this(System::nanoTime);
    }

    CatalogQueryCache(LongSupplier ticker) {
        this.ticker = ticker;
    }

    CatalogPageResponse<CatalogProductListItemResponse> get(
            CatalogProductSearchRequest request,
            Supplier<CatalogPageResponse<CatalogProductListItemResponse>> loader
    ) {
        long now = ticker.getAsLong();
        removeExpiredEntries(now);
        if (!entries.containsKey(request) && entries.size() >= MAX_ENTRIES) {
            entries.clear();
        }

        return entries.compute(request, (key, cached) -> {
            if (cached != null && cached.expiresAtNanos() > now) {
                return cached;
            }
            return new CacheEntry(loader.get(), now + TTL.toNanos());
        }).response();
    }

    void invalidateAll() {
        entries.clear();
    }

    int size() {
        return entries.size();
    }

    private void removeExpiredEntries(long now) {
        entries.entrySet().removeIf(entry -> entry.getValue().expiresAtNanos() <= now);
    }

    private record CacheEntry(
            CatalogPageResponse<CatalogProductListItemResponse> response,
            long expiresAtNanos
    ) {
    }
}
