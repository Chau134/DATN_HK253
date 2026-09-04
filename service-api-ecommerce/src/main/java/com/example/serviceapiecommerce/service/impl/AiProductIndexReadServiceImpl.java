package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductCategory;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.mapper.AiProductIndexItemMapper;
import com.example.serviceapiecommerce.repository.ProductAttributeRepository;
import com.example.serviceapiecommerce.repository.ProductCategoryRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.service.AiProductIndexReadService;
import jakarta.persistence.EntityNotFoundException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AiProductIndexReadServiceImpl implements AiProductIndexReadService {
    private static final int DEFAULT_PAGE_SIZE = 100;

    private final ProductRepository productRepository;
    private final ProductImageRepository productImageRepository;
    private final ProductCategoryRepository productCategoryRepository;
    private final ProductVariantRepository productVariantRepository;
    private final ProductPriceRepository productPriceRepository;
    private final ProductAttributeRepository productAttributeRepository;
    private final AiProductIndexItemMapper mapper;

    public AiProductIndexReadServiceImpl(
            ProductRepository productRepository,
            ProductImageRepository productImageRepository,
            ProductCategoryRepository productCategoryRepository,
            ProductVariantRepository productVariantRepository,
            ProductPriceRepository productPriceRepository,
            ProductAttributeRepository productAttributeRepository,
            AiProductIndexItemMapper mapper
    ) {
        this.productRepository = productRepository;
        this.productImageRepository = productImageRepository;
        this.productCategoryRepository = productCategoryRepository;
        this.productVariantRepository = productVariantRepository;
        this.productPriceRepository = productPriceRepository;
        this.productAttributeRepository = productAttributeRepository;
        this.mapper = mapper;
    }

    @Override
    public AiProductIndexItemDto getProductForAiIndex(Long productId) {
        if (productId == null) {
            throw new IllegalArgumentException("productId must not be null");
        }

        Product product = productRepository.findForAiIndexingById(productId)
                .orElseThrow(() -> new EntityNotFoundException("Product not found: " + productId));

        return mapper.toDto(
                product,
                productImageRepository.findByProductIdOrderBySortOrder(productId),
                productCategoryRepository.findByProductIdWithCategory(productId),
                productVariantRepository.findByProductId(productId),
                productPriceRepository.findFirstByProduct_IdOrderByUpdatedAtDescIdDesc(productId).orElse(null),
                productAttributeRepository.findByProductId(productId)
        );
    }

    @Override
    public Page<AiProductIndexItemDto> getProductsForFullSync(Pageable pageable) {
        Pageable resolvedPageable = stablePageable(pageable);
        Page<Product> productPage = productRepository.findAllSearchableProducts(resolvedPageable);
        return mapProductPage(productPage);
    }

    @Override
    public Page<AiProductIndexItemDto> getProductsUpdatedAfter(Instant updatedAfter, Pageable pageable) {
        if (updatedAfter == null) {
            throw new IllegalArgumentException("updatedAfter must not be null");
        }

        Pageable resolvedPageable = stablePageable(pageable);
        Page<Product> productPage = productRepository.findProductsUpdatedAfter(updatedAfter, resolvedPageable);
        return mapProductPage(productPage);
    }

    private Page<AiProductIndexItemDto> mapProductPage(Page<Product> productPage) {
        List<Product> products = productPage.getContent();
        if (products.isEmpty()) {
            return new PageImpl<>(List.of(), productPage.getPageable(), productPage.getTotalElements());
        }

        List<Long> productIds = products.stream()
                .map(Product::getId)
                .toList();

        Map<Long, List<ProductImage>> imagesByProductId = groupByProductId(
                productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds),
                image -> image.getProduct().getId()
        );
        Map<Long, List<ProductCategory>> categoriesByProductId = groupByProductId(
                productCategoryRepository.findByProductIdInWithCategory(productIds),
                productCategory -> productCategory.getProduct().getId()
        );
        Map<Long, List<ProductVariant>> variantsByProductId = groupByProductId(
                productVariantRepository.findByProductIdIn(productIds),
                variant -> variant.getProduct().getId()
        );
        Map<Long, ProductPrice> priceByProductId = latestPriceByProductId(
                productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds)
        );
        Map<Long, List<ProductAttribute>> attributesByProductId = groupByProductId(
                productAttributeRepository.findByProductIdIn(productIds),
                attribute -> attribute.getProduct().getId()
        );

        List<AiProductIndexItemDto> items = mapper.toDtos(
                products,
                imagesByProductId,
                categoriesByProductId,
                variantsByProductId,
                priceByProductId,
                attributesByProductId
        );
        return new PageImpl<>(items, productPage.getPageable(), productPage.getTotalElements());
    }

    private static Pageable stablePageable(Pageable pageable) {
        if (pageable == null) {
            return PageRequest.of(0, DEFAULT_PAGE_SIZE, Sort.by("id").ascending());
        }
        if (pageable.isUnpaged() || pageable.getSort().isSorted()) {
            return pageable;
        }
        return PageRequest.of(pageable.getPageNumber(), pageable.getPageSize(), Sort.by("id").ascending());
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
}
