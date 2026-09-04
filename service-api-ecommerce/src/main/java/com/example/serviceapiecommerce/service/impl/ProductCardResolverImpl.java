package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.response.ProductCardResponse;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.mapper.AiProductAvailabilityPolicy;
import com.example.serviceapiecommerce.repository.ProductAttributeRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.service.ProductCardResolver;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class ProductCardResolverImpl implements ProductCardResolver {
    private static final String DEFAULT_CURRENCY = "VND";

    private final ProductRepository productRepository;
    private final ProductImageRepository productImageRepository;
    private final ProductPriceRepository productPriceRepository;
    private final ProductVariantRepository productVariantRepository;
    private final ProductAttributeRepository productAttributeRepository;

    public ProductCardResolverImpl(
            ProductRepository productRepository,
            ProductImageRepository productImageRepository,
            ProductPriceRepository productPriceRepository,
            ProductVariantRepository productVariantRepository,
            ProductAttributeRepository productAttributeRepository
    ) {
        this.productRepository = productRepository;
        this.productImageRepository = productImageRepository;
        this.productPriceRepository = productPriceRepository;
        this.productVariantRepository = productVariantRepository;
        this.productAttributeRepository = productAttributeRepository;
    }

    @Override
    public List<ProductCardResponse> resolve(List<AiProductResultDto> rankedResults) {
        if (rankedResults == null || rankedResults.isEmpty()) {
            return List.of();
        }

        List<RankedProductId> rankedProductIds = dedupeByProductId(rankedResults.stream()
                .map(ProductCardResolverImpl::toRankedProductId)
                .filter(Objects::nonNull)
                .toList());
        if (rankedProductIds.isEmpty()) {
            return List.of();
        }

        List<Long> productIds = rankedProductIds.stream()
                .map(RankedProductId::productId)
                .toList();
        Map<Long, Product> productById = toMap(productRepository.findAllByIdInForAiIndexing(productIds), Product::getId);
        Map<Long, List<ProductImage>> imagesByProductId = groupByProductId(
                productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds),
                image -> image.getProduct().getId()
        );
        Map<Long, ProductPrice> latestPriceByProductId = latestPriceByProductId(
                productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds)
        );
        Map<Long, List<ProductVariant>> variantsByProductId = groupByProductId(
                productVariantRepository.findByProductIdIn(productIds),
                variant -> variant.getProduct().getId()
        );
        Map<Long, List<ProductAttribute>> attributesByProductId = groupByProductId(
                productAttributeRepository.findByProductIdIn(productIds),
                attribute -> attribute.getProduct().getId()
        );

        List<ProductCardResponse> cards = new ArrayList<>();
        for (RankedProductId rankedProductId : rankedProductIds) {
            Product product = productById.get(rankedProductId.productId());
            if (product == null) {
                continue;
            }
            List<ProductVariant> variants = variantsByProductId.getOrDefault(product.getId(), List.of());
            List<ProductAttribute> attributes = attributesByProductId.getOrDefault(product.getId(), List.of());
            if (!isActive(variants, attributes)) {
                continue;
            }
            cards.add(toCard(
                    product,
                    imagesByProductId.getOrDefault(product.getId(), List.of()),
                    latestPriceByProductId.get(product.getId()),
                    variants,
                    attributes,
                    rankedProductId.result()
            ));
        }
        return cards;
    }

    private static ProductCardResponse toCard(
            Product product,
            List<ProductImage> images,
            ProductPrice price,
            List<ProductVariant> variants,
            List<ProductAttribute> attributes,
            AiProductResultDto aiResult
    ) {
        List<String> imageUrls = imageUrls(product, images);
        return new ProductCardResponse(
                String.valueOf(product.getId()),
                product.getExternalId(),
                product.getProductDisplayName(),
                product.getProductDisplayNameVi(),
                product.getBrandName(),
                price == null ? null : price.getSellingPrice(),
                null,
                effectivePrice(price),
                DEFAULT_CURRENCY,
                totalStock(variants, attributes),
                available(variants, attributes),
                imageUrls.isEmpty() ? null : imageUrls.getFirst(),
                imageUrls,
                aiResult.score(),
                aiResult.source()
        );
    }

    private static RankedProductId toRankedProductId(AiProductResultDto result) {
        if (result == null || result.productId() == null || result.productId().isBlank()) {
            return null;
        }
        try {
            return new RankedProductId(Long.parseLong(result.productId()), result);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private static List<RankedProductId> dedupeByProductId(List<RankedProductId> rankedProductIds) {
        Map<Long, RankedProductId> deduped = new LinkedHashMap<>();
        for (RankedProductId rankedProductId : rankedProductIds) {
            deduped.putIfAbsent(rankedProductId.productId(), rankedProductId);
        }
        return List.copyOf(deduped.values());
    }

    private static List<String> imageUrls(Product product, List<ProductImage> images) {
        List<String> urls = images.stream()
                .map(ProductImage::getImageUrl)
                .filter(ProductCardResolverImpl::hasText)
                .distinct()
                .toList();
        if (!urls.isEmpty() || !hasText(product.getMainImage())) {
            return urls;
        }
        return List.of(product.getMainImage());
    }

    private static BigDecimal effectivePrice(ProductPrice price) {
        if (price == null) {
            return null;
        }
        return price.getSellingPrice();
    }

    private static Integer totalStock(
            List<ProductVariant> variants,
            List<ProductAttribute> attributes
    ) {
        return AiProductAvailabilityPolicy.inventoryCount(variants, attributes);
    }

    private static Boolean available(
            List<ProductVariant> variants,
            List<ProductAttribute> attributes
    ) {
        return AiProductAvailabilityPolicy.available(variants, attributes);
    }

    private static boolean isActive(
            List<ProductVariant> variants,
            List<ProductAttribute> attributes
    ) {
        return AiProductAvailabilityPolicy.productActive(variants, attributes);
    }

    private static <T> Map<Long, T> toMap(Collection<T> values, Function<T, Long> idExtractor) {
        Map<Long, T> byId = new LinkedHashMap<>();
        for (T value : values) {
            byId.putIfAbsent(idExtractor.apply(value), value);
        }
        return byId;
    }

    private static <T> Map<Long, List<T>> groupByProductId(
            Collection<T> values,
            Function<T, Long> productIdExtractor
    ) {
        Map<Long, List<T>> grouped = new LinkedHashMap<>();
        for (T value : values) {
            Long productId = productIdExtractor.apply(value);
            grouped.computeIfAbsent(productId, ignored -> new ArrayList<>()).add(value);
        }
        return grouped;
    }

    private static Map<Long, ProductPrice> latestPriceByProductId(Collection<ProductPrice> prices) {
        Map<Long, ProductPrice> latestByProductId = new LinkedHashMap<>();
        for (ProductPrice price : prices) {
            latestByProductId.putIfAbsent(price.getProduct().getId(), price);
        }
        return latestByProductId;
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private record RankedProductId(Long productId, AiProductResultDto result) {
    }
}
