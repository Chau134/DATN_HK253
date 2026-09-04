package com.example.serviceapiecommerce.mapper;

import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductVariant;
import java.time.Instant;
import java.util.Collection;
import java.util.Comparator;
import java.util.Objects;
import java.util.Optional;

public final class AiProductAvailabilityPolicy {
    public static final String ACTIVE_ATTRIBUTE_KEY = "flag:active";

    private AiProductAvailabilityPolicy() {
    }

    public static boolean productActive(
            Collection<ProductVariant> variants,
            Collection<ProductAttribute> attributes
    ) {
        Optional<Boolean> productOverride = latestActiveOverride(attributes);
        if (productOverride.isPresent()) {
            return productOverride.get();
        }
        return safe(variants).stream().anyMatch(variant -> Boolean.TRUE.equals(variant.getActive()));
    }

    public static boolean available(
            Collection<ProductVariant> variants,
            Collection<ProductAttribute> attributes
    ) {
        return productActive(variants, attributes)
                && safe(variants).stream().anyMatch(AiProductAvailabilityPolicy::sellableVariant);
    }

    public static int inventoryCount(
            Collection<ProductVariant> variants,
            Collection<ProductAttribute> attributes
    ) {
        if (!productActive(variants, attributes)) {
            return 0;
        }
        return safe(variants).stream()
                .filter(AiProductAvailabilityPolicy::sellableVariant)
                .map(ProductVariant::getInventoryCount)
                .filter(Objects::nonNull)
                .reduce(0, Integer::sum);
    }

    public static boolean sellableVariant(ProductVariant variant) {
        Integer inventoryCount = variant.getInventoryCount();
        return Boolean.TRUE.equals(variant.getActive())
                && Boolean.TRUE.equals(variant.getAvailable())
                && inventoryCount != null
                && inventoryCount > 0;
    }

    private static Optional<Boolean> latestActiveOverride(Collection<ProductAttribute> attributes) {
        return safe(attributes).stream()
                .filter(attribute -> ACTIVE_ATTRIBUTE_KEY.equals(attribute.getAttrKey()))
                .filter(attribute -> parseBoolean(attribute.getAttrValue()).isPresent())
                .max(Comparator
                        .comparing(
                                ProductAttribute::getUpdatedAt,
                                Comparator.nullsFirst(Instant::compareTo)
                        )
                        .thenComparing(
                                ProductAttribute::getId,
                                Comparator.nullsFirst(Long::compareTo)
                        ))
                .flatMap(attribute -> parseBoolean(attribute.getAttrValue()));
    }

    private static Optional<Boolean> parseBoolean(String value) {
        if (value == null) {
            return Optional.empty();
        }
        String normalized = value.trim();
        if ("true".equalsIgnoreCase(normalized)) {
            return Optional.of(true);
        }
        if ("false".equalsIgnoreCase(normalized)) {
            return Optional.of(false);
        }
        return Optional.empty();
    }

    private static <T> Collection<T> safe(Collection<T> values) {
        return values == null ? java.util.List.of() : values;
    }
}
