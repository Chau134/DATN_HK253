package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.config.AiServiceProperties;
import com.example.serviceapiecommerce.dto.ai.AiIndexBatchResponse;
import com.example.serviceapiecommerce.dto.ai.AiIndexFailureDto;
import com.example.serviceapiecommerce.dto.ai.AiIndexSingleResponse;
import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import com.example.serviceapiecommerce.dto.ai.AiSyncResponse;
import com.example.serviceapiecommerce.repository.AiSyncStateRepository;
import com.example.serviceapiecommerce.service.AiProductIndexReadService;
import com.example.serviceapiecommerce.service.AiProductSyncService;
import com.example.serviceapiecommerce.service.AiServiceClient;
import java.time.Clock;
import java.time.Instant;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

@Service
public class AiProductSyncServiceImpl implements AiProductSyncService {
    private static final Logger log = LoggerFactory.getLogger(AiProductSyncServiceImpl.class);
    private static final String PRODUCT_INDEX_SYNC = "product_index";
    private static final String FULL_SYNC = "full";
    private static final String LIMITED_FULL_SYNC = "limited_full";
    private static final String INCREMENTAL_SYNC = "incremental";
    private static final Instant INITIAL_SYNC_INSTANT = Instant.EPOCH;

    private final AiProductIndexReadService readService;
    private final AiServiceClient aiServiceClient;
    private final AiSyncStateRepository syncStateRepository;
    private final AiServiceProperties properties;
    private final Clock clock;

    @Autowired
    public AiProductSyncServiceImpl(
            AiProductIndexReadService readService,
            AiServiceClient aiServiceClient,
            AiSyncStateRepository syncStateRepository,
            AiServiceProperties properties
    ) {
        this(readService, aiServiceClient, syncStateRepository, properties, Clock.systemUTC());
    }

    AiProductSyncServiceImpl(
            AiProductIndexReadService readService,
            AiServiceClient aiServiceClient,
            AiSyncStateRepository syncStateRepository,
            AiServiceProperties properties,
            Clock clock
    ) {
        this.readService = readService;
        this.aiServiceClient = aiServiceClient;
        this.syncStateRepository = syncStateRepository;
        this.properties = properties;
        this.clock = clock;
    }

    @Override
    public AiSyncResponse runFullSync() {
        Instant startedAt = Instant.now(clock);
        Instant previousSuccessAt = syncStateRepository.findLastSuccessAt(PRODUCT_INDEX_SYNC).orElse(null);
        return runPagedSync(
                FULL_SYNC,
                previousSuccessAt,
                startedAt,
                readService::getProductsForFullSync
        );
    }

    @Override
    public AiSyncResponse runLimitedFullSync(int limit) {
        int resolvedLimit = Math.max(limit, 1);
        Instant startedAt = Instant.now(clock);
        Instant previousSuccessAt = syncStateRepository.findLastSuccessAt(PRODUCT_INDEX_SYNC).orElse(null);
        return runPagedSync(
                LIMITED_FULL_SYNC,
                previousSuccessAt,
                startedAt,
                pageable -> readService.getProductsForFullSync(limitedPageable(pageable, resolvedLimit)),
                resolvedLimit,
                false
        );
    }

    @Override
    public AiSyncResponse runIncrementalSync() {
        Instant startedAt = Instant.now(clock);
        Instant previousSuccessAt = syncStateRepository.findLastSuccessAt(PRODUCT_INDEX_SYNC).orElse(null);
        Instant updatedAfter = previousSuccessAt == null ? INITIAL_SYNC_INSTANT : previousSuccessAt;
        return runPagedSync(
                INCREMENTAL_SYNC,
                previousSuccessAt,
                startedAt,
                pageable -> readService.getProductsUpdatedAfter(updatedAfter, pageable)
        );
    }

    @Override
    public AiIndexSingleResponse syncProduct(Long productId) {
        AiProductIndexItemDto item = readService.getProductForAiIndex(productId);
        AiIndexSingleResponse response = aiServiceClient.indexProduct(item);
        if (response.failedCount() > 0) {
            log.warn(
                    "ai_manual_product_sync_failed product_id={} failures={}",
                    item.productId(),
                    response.failures()
            );
        }
        return response;
    }

    private AiSyncResponse runPagedSync(
            String syncType,
            Instant previousSuccessAt,
            Instant cursorToStoreOnSuccess,
            Function<Pageable, Page<AiProductIndexItemDto>> pageReader
    ) {
        return runPagedSync(syncType, previousSuccessAt, cursorToStoreOnSuccess, pageReader, null, true);
    }

    private AiSyncResponse runPagedSync(
            String syncType,
            Instant previousSuccessAt,
            Instant cursorToStoreOnSuccess,
            Function<Pageable, Page<AiProductIndexItemDto>> pageReader,
            Integer maxItems,
            boolean markSuccessfulCursor
    ) {
        int batchSize = Math.max(properties.batchSize(), 1);
        long totalCount = 0L;
        long successCount = 0L;
        long failureCount = 0L;
        long imageIndexedCount = 0L;
        long imageFailureCount = 0L;
        int batchCount = 0;
        Set<String> failedProductIds = new LinkedHashSet<>();
        Set<String> warnings = new LinkedHashSet<>();

        Page<AiProductIndexItemDto> page;
        int pageNumber = 0;
        do {
            page = pageReader.apply(PageRequest.of(pageNumber, batchSize, Sort.by("id").ascending()));
            totalCount = maxItems == null ? page.getTotalElements() : Math.min(page.getTotalElements(), maxItems);

            List<AiProductIndexItemDto> items = page.getContent();
            if (maxItems != null) {
                int remaining = maxItems - (int) (successCount + failureCount);
                if (remaining <= 0) {
                    break;
                }
                if (items.size() > remaining) {
                    items = items.subList(0, remaining);
                }
            }
            if (!items.isEmpty()) {
                batchCount++;
                AiIndexBatchResponse batchResponse = aiServiceClient.indexProducts(items);
                successCount += batchResponse.indexedCount();
                failureCount += batchResponse.failedCount();
                imageIndexedCount += batchResponse.imageIndexedCount();
                imageFailureCount += batchResponse.imageFailedCount();
                warnings.addAll(batchResponse.warnings());

                List<String> batchFailedProductIds = failedProductIdsForBatch(items, batchResponse);
                failedProductIds.addAll(batchFailedProductIds);
                logBatchFailures(syncType, pageNumber, batchFailedProductIds, batchResponse);
            }

            pageNumber++;
        } while (page.hasNext() && (maxItems == null || successCount + failureCount < maxItems));

        Instant newLastSuccessAt = null;
        if (failureCount == 0L && markSuccessfulCursor) {
            syncStateRepository.markSuccessfulSync(PRODUCT_INDEX_SYNC, cursorToStoreOnSuccess);
            newLastSuccessAt = cursorToStoreOnSuccess;
        }

        return new AiSyncResponse(
                PRODUCT_INDEX_SYNC,
                syncType,
                totalCount,
                successCount,
                failureCount,
                batchCount,
                imageIndexedCount,
                imageFailureCount,
                List.copyOf(failedProductIds),
                List.copyOf(warnings),
                previousSuccessAt,
                newLastSuccessAt
        );
    }

    private static Pageable limitedPageable(Pageable pageable, int limit) {
        int remaining = limit - (pageable.getPageNumber() * pageable.getPageSize());
        int pageSize = Math.max(0, Math.min(pageable.getPageSize(), remaining));
        return PageRequest.of(pageable.getPageNumber(), Math.max(pageSize, 1), pageable.getSort());
    }

    private static List<String> failedProductIdsForBatch(
            List<AiProductIndexItemDto> items,
            AiIndexBatchResponse response
    ) {
        List<String> failedIds = response.failures().stream()
                .filter(failure -> failure.imageUrl() == null)
                .map(AiIndexFailureDto::productId)
                .filter(AiProductSyncServiceImpl::hasText)
                .distinct()
                .toList();

        if (response.failedCount() > 0 && failedIds.isEmpty()) {
            return items.stream()
                    .map(AiProductIndexItemDto::productId)
                    .filter(AiProductSyncServiceImpl::hasText)
                    .toList();
        }

        return failedIds;
    }

    private static void logBatchFailures(
            String syncType,
            int pageNumber,
            List<String> failedProductIds,
            AiIndexBatchResponse response
    ) {
        if (response.failedCount() <= 0 && response.imageFailedCount() <= 0) {
            return;
        }

        if (!failedProductIds.isEmpty()) {
            log.warn(
                    "ai_product_sync_batch_failed_products sync_type={} page={} product_ids={}",
                    syncType,
                    pageNumber,
                    failedProductIds
            );
        }

        for (AiIndexFailureDto failure : response.failures().stream()
                .filter(item -> item.imageUrl() == null)
                .toList()) {
            log.warn(
                    "ai_product_sync_failure sync_type={} product_id={} stage={} reason={}",
                    syncType,
                    failure.productId(),
                    failure.stage(),
                    failure.reason()
            );
        }

        Map<String, Long> imageFailureSummary = response.failures().stream()
                .filter(item -> item.imageUrl() != null)
                .collect(Collectors.groupingBy(
                        item -> item.stage() + ":" + item.reason(),
                        Collectors.counting()
                ));
        if (!imageFailureSummary.isEmpty()) {
            log.warn(
                    "ai_product_sync_image_failures sync_type={} page={} failure_count={} summary={}",
                    syncType,
                    pageNumber,
                    response.imageFailedCount(),
                    imageFailureSummary
            );
        }
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
