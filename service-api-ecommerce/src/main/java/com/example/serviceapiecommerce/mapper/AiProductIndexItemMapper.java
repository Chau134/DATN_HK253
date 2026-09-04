package com.example.serviceapiecommerce.mapper;

import com.example.serviceapiecommerce.dto.ai.AiCategoryDto;
import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import com.example.serviceapiecommerce.entity.Category;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductCategory;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class AiProductIndexItemMapper {
    private static final Set<String> VIDEO_PATH_EXTENSIONS = Set.of(
            ".m3u8",
            ".mp4",
            ".mov",
            ".m4v",
            ".webm",
            ".avi",
            ".mkv"
    );

    private static final List<String> SEARCH_ATTRIBUTE_KEYS = List.of(
            "search_category",
            "search_category_vi",
            "search_attributes",
            "search_attributes_vi",
            "search_keywords_vi"
    );

    public AiProductIndexItemDto toDto(
            Product product,
            Collection<ProductImage> images,
            Collection<ProductCategory> productCategories,
            Collection<ProductVariant> variants,
            ProductPrice price,
            Collection<ProductAttribute> attributes
    ) {
        List<ProductVariant> resolvedVariants = listOrEmpty(variants);
        List<ProductAttribute> resolvedAttributes = listOrEmpty(attributes);

        return new AiProductIndexItemDto(
                String.valueOf(product.getId()),
                product.getProductDisplayName(),
                product.getProductDisplayNameVi(),
                product.getBrandName(),
                product.getBaseColour(),
                product.getBaseColourVi(),
                product.getMaterial(),
                product.getMaterialVi(),
                product.getFit(),
                product.getFitVi(),
                product.getSeason(),
                product.getSeasonVi(),
                product.getProductUsage(),
                product.getProductUsageVi(),
                product.getGender(),
                product.getGenderVi(),
                product.getDescription(),
                product.getDescriptionVi(),
                mapCategories(productCategories),
                mapVariantValues(resolvedVariants, false),
                mapVariantValues(resolvedVariants, true),
                AiProductAvailabilityPolicy.inventoryCount(resolvedVariants, resolvedAttributes),
                AiProductAvailabilityPolicy.available(resolvedVariants, resolvedAttributes),
                AiProductAvailabilityPolicy.productActive(resolvedVariants, resolvedAttributes),
                price == null ? null : price.getSellingPrice(),
                price == null ? null : price.getVat(),
                imageUrls(product, images),
                attributes(resolvedAttributes, false),
                attributes(resolvedAttributes, true),
                product.getUpdatedAt()
        );
    }

    public List<AiProductIndexItemDto> toDtos(
            Collection<Product> products,
            Map<Long, ? extends Collection<ProductImage>> imagesByProductId,
            Map<Long, ? extends Collection<ProductCategory>> categoriesByProductId,
            Map<Long, ? extends Collection<ProductVariant>> variantsByProductId,
            Map<Long, ProductPrice> priceByProductId,
            Map<Long, ? extends Collection<ProductAttribute>> attributesByProductId
    ) {
        return listOrEmpty(products).stream()
                .map(product -> toDto(
                        product,
                        collectionForProduct(imagesByProductId, product.getId()),
                        collectionForProduct(categoriesByProductId, product.getId()),
                        collectionForProduct(variantsByProductId, product.getId()),
                        priceForProduct(priceByProductId, product.getId()),
                        collectionForProduct(attributesByProductId, product.getId())
                ))
                .toList();
    }

    private static List<AiCategoryDto> mapCategories(Collection<ProductCategory> productCategories) {
        return listOrEmpty(productCategories).stream()
                .map(ProductCategory::getCategory)
                .filter(Objects::nonNull)
                .sorted(Comparator
                        .comparing(Category::getCategoryLevel, Comparator.nullsLast(String::compareTo))
                        .thenComparing(Category::getCategoryName, Comparator.nullsLast(String::compareTo))
                        .thenComparing(Category::getId, Comparator.nullsLast(Long::compareTo)))
                .map(category -> new AiCategoryDto(
                        category.getCanonicalCode(),
                        category.getCategoryLevel(),
                        category.getCategoryName(),
                        category.getCategoryNameVi()
                ))
                .toList();
    }

    private static List<String> mapVariantValues(Collection<ProductVariant> variants, boolean unified) {
        List<String> values = new ArrayList<>();
        for (ProductVariant variant : variants) {
            addIfPresent(values, unified ? variant.getUnifiedSize() : variant.getOptionValue());
        }
        return values;
    }

    private static List<String> imageUrls(Product product, Collection<ProductImage> images) {
        List<String> urls = listOrEmpty(images).stream()
                .filter(image -> isImageIndexingUrl(image.getImageUrl()))
                .sorted(Comparator
                        .comparing(ProductImage::getSortOrder, Comparator.nullsLast(Integer::compareTo))
                        .thenComparing(ProductImage::getId, Comparator.nullsLast(Long::compareTo)))
                .map(image -> image.getImageUrl().trim())
                .distinct()
                .toList();

        if (!urls.isEmpty()) {
            return urls;
        }
        if (isImageIndexingUrl(product.getMainImage())) {
            return compactDistinct(product.getMainImage());
        }
        return List.of();
    }

    private static boolean isImageIndexingUrl(String value) {
        if (!hasText(value)) {
            return false;
        }

        final String path;
        try {
            path = new URI(value.trim()).getPath();
        } catch (URISyntaxException exception) {
            return false;
        }
        if (!hasText(path)) {
            return false;
        }

        String normalizedPath = path.toLowerCase(Locale.ROOT);
        return VIDEO_PATH_EXTENSIONS.stream().noneMatch(normalizedPath::endsWith);
    }

    private static Map<String, String> attributes(
            Collection<ProductAttribute> attributes,
            boolean vietnamese
    ) {
        Map<String, String> result = new LinkedHashMap<>();
        for (ProductAttribute attribute : attributes) {
            String value = vietnamese ? attribute.getAttrValueVi() : attribute.getAttrValue();
            if (SEARCH_ATTRIBUTE_KEYS.contains(attribute.getAttrKey()) && hasText(value)) {
                result.put(attribute.getAttrKey(), value);
            }
        }
        return result;
    }

    private static <T> List<T> listOrEmpty(Collection<T> values) {
        if (values == null) {
            return List.of();
        }
        return List.copyOf(values);
    }

    private static <T> Collection<T> collectionForProduct(
            Map<Long, ? extends Collection<T>> valuesByProductId,
            Long productId
    ) {
        if (valuesByProductId == null) {
            return List.of();
        }
        Collection<T> values = valuesByProductId.get(productId);
        return values == null ? List.of() : values;
    }

    private static ProductPrice priceForProduct(Map<Long, ProductPrice> valuesByProductId, Long productId) {
        if (valuesByProductId == null) {
            return null;
        }
        return valuesByProductId.get(productId);
    }

    private static List<String> compactDistinct(String... values) {
        List<String> result = new ArrayList<>();
        for (String value : values) {
            addIfPresent(result, value);
        }
        return result;
    }

    private static void addIfPresent(List<String> values, String value) {
        if (hasText(value) && !values.contains(value.trim())) {
            values.add(value.trim());
        }
    }

    private static boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }
}
