package com.example.serviceapiecommerce.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;

import com.example.serviceapiecommerce.dto.catalog.CatalogPageResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductListItemResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductSearchRequest;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;

class CatalogQueryCacheTest {
    private static final CatalogProductSearchRequest REQUEST = new CatalogProductSearchRequest(
            null, null, null, null, null, null, null, 0, 20, "newest"
    );

    @Test
    void reusesResponseUntilTtlExpires() {
        AtomicLong ticker = new AtomicLong();
        AtomicInteger loads = new AtomicInteger();
        CatalogQueryCache cache = new CatalogQueryCache(ticker::get);

        CatalogPageResponse<CatalogProductListItemResponse> first = cache.get(
                REQUEST,
                () -> response(loads.incrementAndGet())
        );
        CatalogPageResponse<CatalogProductListItemResponse> cached = cache.get(
                REQUEST,
                () -> response(loads.incrementAndGet())
        );

        assertSame(first, cached);
        assertEquals(1, loads.get());

        ticker.set(CatalogQueryCache.TTL.toNanos() + 1);
        CatalogPageResponse<CatalogProductListItemResponse> refreshed = cache.get(
                REQUEST,
                () -> response(loads.incrementAndGet())
        );

        assertEquals(2, loads.get());
        assertEquals(2L, refreshed.totalElements());
    }

    @Test
    void invalidationForcesReload() {
        AtomicInteger loads = new AtomicInteger();
        CatalogQueryCache cache = new CatalogQueryCache(() -> 0L);
        cache.get(REQUEST, () -> response(loads.incrementAndGet()));

        cache.invalidateAll();
        CatalogPageResponse<CatalogProductListItemResponse> refreshed = cache.get(
                REQUEST,
                () -> response(loads.incrementAndGet())
        );

        assertEquals(2, loads.get());
        assertEquals(1, cache.size());
        assertEquals(2L, refreshed.totalElements());
    }

    private static CatalogPageResponse<CatalogProductListItemResponse> response(long marker) {
        return new CatalogPageResponse<>(List.of(), 0, 20, marker, 1, true, true, "newest");
    }
}
