package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.catalog.CatalogCategoryResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogPageResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductDetailResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductImageResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductListItemResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductPriceResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductReviewSummaryResponse;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductSearchRequest;
import com.example.serviceapiecommerce.dto.catalog.CatalogProductVariantResponse;
import com.example.serviceapiecommerce.entity.Category;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductCategory;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductReviewSummary;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.CategoryRepository;
import com.example.serviceapiecommerce.repository.ProductCategoryRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductReviewSummaryRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.repository.PromotionRepository;
import com.example.serviceapiecommerce.repository.PromotionProductRepository;
import com.example.serviceapiecommerce.repository.PromotionCategoryRepository;
import com.example.serviceapiecommerce.service.CatalogService;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Expression;
import jakarta.persistence.criteria.Path;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import jakarta.persistence.criteria.Subquery;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.HashSet;
import java.util.function.Function;
import java.time.Instant;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@Transactional(readOnly = true)
public class CatalogServiceImpl implements CatalogService {
    private static final String DEFAULT_CURRENCY = "VND";
    private static final int DEFAULT_PAGE_SIZE = 20;
    private static final int MAX_PAGE_SIZE = 100;

    private final ProductRepository productRepository;
    private final ProductImageRepository productImageRepository;
    private final ProductCategoryRepository productCategoryRepository;
    private final ProductVariantRepository productVariantRepository;
    private final ProductPriceRepository productPriceRepository;
    private final ProductReviewSummaryRepository productReviewSummaryRepository;
    private final CategoryRepository categoryRepository;
    private final PromotionRepository promotionRepository;
    private final PromotionProductRepository promotionProductRepository;
    private final PromotionCategoryRepository promotionCategoryRepository;
    private final CatalogQueryCache catalogQueryCache;

    public CatalogServiceImpl(
            ProductRepository productRepository,
            ProductImageRepository productImageRepository,
            ProductCategoryRepository productCategoryRepository,
            ProductVariantRepository productVariantRepository,
            ProductPriceRepository productPriceRepository,
            ProductReviewSummaryRepository productReviewSummaryRepository,
            CategoryRepository categoryRepository,
            PromotionRepository promotionRepository,
            PromotionProductRepository promotionProductRepository,
            PromotionCategoryRepository promotionCategoryRepository,
            CatalogQueryCache catalogQueryCache
    ) {
        this.productRepository = productRepository;
        this.productImageRepository = productImageRepository;
        this.productCategoryRepository = productCategoryRepository;
        this.productVariantRepository = productVariantRepository;
        this.productPriceRepository = productPriceRepository;
        this.productReviewSummaryRepository = productReviewSummaryRepository;
        this.categoryRepository = categoryRepository;
        this.promotionRepository = promotionRepository;
        this.promotionProductRepository = promotionProductRepository;
        this.promotionCategoryRepository = promotionCategoryRepository;
        this.catalogQueryCache = catalogQueryCache;
    }

    @Override
    public CatalogPageResponse<CatalogProductListItemResponse> findProducts(CatalogProductSearchRequest request) {
        CatalogProductSearchRequest resolvedRequest = request == null ? emptyRequest() : request;
        validatePriceRange(resolvedRequest);

        return catalogQueryCache.get(resolvedRequest, () -> findProductsUncached(resolvedRequest));
    }

    private CatalogPageResponse<CatalogProductListItemResponse> findProductsUncached(
            CatalogProductSearchRequest resolvedRequest
    ) {

        List<Long> categoryIds = resolveCategoryIds(resolvedRequest.categoryId());

        ResolvedPageable resolvedPageable = resolvePageable(resolvedRequest);
        Page<Product> productPage = productRepository.findAll(
                productSpecification(resolvedRequest, categoryIds),
                resolvedPageable.pageable()
        );
        Page<CatalogProductListItemResponse> responsePage = mapListPage(productPage);
        return CatalogPageResponse.from(responsePage, resolvedPageable.sort());
    }

    private List<Long> resolveCategoryIds(Long categoryId) {
        if (categoryId == null) {
            return List.of();
        }

        List<Category> allCategories = categoryRepository.findAll();
        Category target = allCategories.stream()
                .filter(c -> c.getId().equals(categoryId))
                .findFirst()
                .orElse(null);
        if (target == null) {
            return List.of(categoryId);
        }

        List<Long> result = new ArrayList<>();
        result.add(categoryId);
        collectDescendants(categoryId, allCategories, result);
        return result;
    }

    private void collectDescendants(Long parentId, List<Category> allCategories, List<Long> result) {
        List<Long> children = allCategories.stream()
                .filter(c -> parentId.equals(c.getParentId()))
                .map(Category::getId)
                .toList();
        for (Long childId : children) {
            if (!result.contains(childId)) {
                result.add(childId);
                collectDescendants(childId, allCategories, result);
            }
        }
    }

    @Override
    public CatalogProductDetailResponse getProduct(Long productId) {
        if (productId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_id_required");
        }

        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_not_found"));
        CatalogHydration hydration = hydrate(List.of(productId));
        return toDetail(product, hydration);
    }

    @Override
    public List<CatalogProductDetailResponse> getProductsByIds(List<Long> productIds) {
        if (productIds == null || productIds.isEmpty()) {
            return List.of();
        }

        List<Long> uniqueProductIds = productIds.stream()
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        if (uniqueProductIds.isEmpty()) {
            return List.of();
        }

        Map<Long, Product> productsById = toMap(
                productRepository.findAllByIdInForAiIndexing(uniqueProductIds),
                Product::getId
        );
        CatalogHydration hydration = hydrate(uniqueProductIds);
        return uniqueProductIds.stream()
                .map(productsById::get)
                .filter(Objects::nonNull)
                .map(product -> toDetail(product, hydration))
                .toList();
    }

    @Override
    public List<CatalogCategoryResponse> getActiveCategories() {
        return categoryRepository.findByIsActiveTrueOrderByCategoryLevelAscCategoryNameAsc()
                .stream()
                .map(CatalogServiceImpl::toCategory)
                .toList();
    }

    @Override
    public List<String> getBrandNames() {
        return productRepository.findDistinctBrandNames();
    }

    private Page<CatalogProductListItemResponse> mapListPage(Page<Product> productPage) {
        List<Product> products = productPage.getContent();
        if (products.isEmpty()) {
            return new PageImpl<>(List.of(), productPage.getPageable(), productPage.getTotalElements());
        }

        List<Long> productIds = products.stream()
                .map(Product::getId)
                .toList();
        CatalogHydration hydration = hydrate(productIds);

        List<CatalogProductListItemResponse> items = products.stream()
                .map(product -> toListItem(product, hydration))
                .toList();
        return new PageImpl<>(items, productPage.getPageable(), productPage.getTotalElements());
    }

    private CatalogHydration hydrate(List<Long> productIds) {
        Map<Long, List<ProductImage>> imagesByProductId = groupByProductId(
                productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds),
                image -> image.getProduct().getId()
        );
        Map<Long, List<ProductCategory>> productCategoriesByProductId = groupByProductId(
                productCategoryRepository.findByProductIdInWithCategory(productIds),
                productCategory -> productCategory.getProduct().getId()
        );
        Map<Long, List<ProductVariant>> variantsByProductId = groupByProductId(
                productVariantRepository.findByProductIdIn(productIds),
                variant -> variant.getProduct().getId()
        );
        Map<Long, ProductPrice> latestPriceByProductId = latestPriceByProductId(
                productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds)
        );
        Map<Long, ProductReviewSummary> reviewSummaryByProductId = toMap(
                productReviewSummaryRepository.findByProduct_IdIn(productIds),
                summary -> summary.getProduct().getId()
        );

        List<com.example.serviceapiecommerce.entity.Promotion> activePromotions = promotionRepository
                .findByStatusOrderByPriorityDescCreatedAtDescIdDesc(com.example.serviceapiecommerce.entity.PromotionStatus.ACTIVE);
        List<Long> promoIds = activePromotions.stream().map(com.example.serviceapiecommerce.entity.Promotion::getId).toList();
        Map<Long, Set<Long>> productTargets = new LinkedHashMap<>();
        Map<Long, Set<Long>> categoryTargets = new LinkedHashMap<>();
        if (!promoIds.isEmpty()) {
            for (com.example.serviceapiecommerce.entity.PromotionProduct pp : promotionProductRepository.findByPromotion_IdInAndActive(promoIds, true)) {
                productTargets.computeIfAbsent(pp.getPromotion().getId(), ignored -> new HashSet<>()).add(pp.getProduct().getId());
            }
            for (com.example.serviceapiecommerce.entity.PromotionCategory pc : promotionCategoryRepository.findByPromotion_IdInAndActive(promoIds, true)) {
                categoryTargets.computeIfAbsent(pc.getPromotion().getId(), ignored -> new HashSet<>()).add(pc.getCategory().getId());
            }
        }

        return new CatalogHydration(
                imagesByProductId,
                productCategoriesByProductId,
                variantsByProductId,
                latestPriceByProductId,
                reviewSummaryByProductId,
                activePromotions,
                productTargets,
                categoryTargets
        );
    }

    private BigDecimal calculateDiscountedPrice(
            Product product,
            BigDecimal sellingPrice,
            CatalogHydration hydration
    ) {
        if (sellingPrice == null || hydration.activePromotions().isEmpty()) {
            return null;
        }

        List<ProductCategory> productCategories = hydration.productCategoriesByProductId().get(product.getId());
        Set<Long> productCategoryIds = new java.util.HashSet<>();
        if (productCategories != null) {
            for (ProductCategory pc : productCategories) {
                productCategoryIds.add(pc.getCategory().getId());
            }
        }

        BigDecimal currentPrice = sellingPrice;
        Instant now = Instant.now();

        for (com.example.serviceapiecommerce.entity.Promotion promotion : hydration.activePromotions()) {
            // Check time window
            if (promotion.getStartsAt() != null && promotion.getStartsAt().isAfter(now)) {
                continue;
            }
            if (promotion.getEndsAt() != null && !promotion.getEndsAt().isAfter(now)) {
                continue;
            }
            // Check currency
            if (promotion.getCurrency() != null && !promotion.getCurrency().equalsIgnoreCase("VND")) {
                continue;
            }
            // Check scope (must be ALL or guest-accessible, i.e. not targeting a specific user)
            if (promotion.getCustomerScope() == com.example.serviceapiecommerce.entity.PromotionCustomerScope.SPECIFIC_CUSTOMER) {
                continue;
            }
            // Check min order amount (if min order amount is greater than the selling price, it doesn't apply to this single product listing)
            if (promotion.getMinOrderAmount() != null) {
                if (promotion.getMinOrderAmount().compareTo(sellingPrice) > 0) {
                    continue;
                }
            }

            // Check targets
            Set<Long> pIds = hydration.promotionProductTargets().getOrDefault(promotion.getId(), Set.of());
            Set<Long> cIds = hydration.promotionCategoryTargets().getOrDefault(promotion.getId(), Set.of());
            boolean hasTargets = !pIds.isEmpty() || !cIds.isEmpty();
            boolean applicable = false;
            if (!hasTargets) {
                applicable = true;
            } else {
                if (pIds.contains(product.getId())) {
                    applicable = true;
                } else {
                    for (Long catId : productCategoryIds) {
                        if (cIds.contains(catId)) {
                            applicable = true;
                            break;
                        }
                    }
                }
            }

            if (!applicable) {
                continue;
            }

            // Calculate discount
            BigDecimal discount = BigDecimal.ZERO;
            if (promotion.getDiscountType() == com.example.serviceapiecommerce.entity.DiscountType.PERCENTAGE) {
                discount = currentPrice.multiply(promotion.getDiscountValue())
                        .divide(BigDecimal.valueOf(100), 2, java.math.RoundingMode.HALF_UP);
            } else if (promotion.getDiscountType() == com.example.serviceapiecommerce.entity.DiscountType.FIXED_AMOUNT) {
                discount = promotion.getDiscountValue();
            }

            if (promotion.getMaxDiscountAmount() != null) {
                discount = discount.min(promotion.getMaxDiscountAmount());
            }

            BigDecimal nextPrice = currentPrice.subtract(discount).max(BigDecimal.ZERO);
            if (nextPrice.compareTo(currentPrice) < 0) {
                currentPrice = nextPrice;
                if (!Boolean.TRUE.equals(promotion.getStackable())) {
                    break;
                }
            }
        }

        if (currentPrice.compareTo(sellingPrice) < 0) {
            return currentPrice.setScale(2, java.math.RoundingMode.HALF_UP);
        }
        return null;
    }

    private CatalogProductListItemResponse toListItem(Product product, CatalogHydration hydration) {
        List<ProductImage> images = hydration.imagesByProductId().getOrDefault(product.getId(), List.of());
        List<ProductVariant> variants = hydration.variantsByProductId().getOrDefault(product.getId(), List.of());
        List<String> imageUrls = imageUrls(product, images);
        ProductPrice price = hydration.latestPriceByProductId().get(product.getId());
        BigDecimal discountedPrice = price == null ? null : calculateDiscountedPrice(product, price.getSellingPrice(), hydration);
        return new CatalogProductListItemResponse(
                product.getId(),
                product.getExternalId(),
                product.getProductDisplayName(),
                product.getProductDisplayNameVi(),
                product.getBrandName(),
                product.getGender(),
                product.getGenderVi(),
                product.getBaseColour(),
                product.getBaseColourVi(),
                toPrice(price, discountedPrice),
                imageUrls.isEmpty() ? null : imageUrls.getFirst(),
                imageUrls,
                toCategories(hydration.productCategoriesByProductId().getOrDefault(product.getId(), List.of())),
                toReviewSummary(hydration.reviewSummaryByProductId().get(product.getId())),
                totalStock(variants),
                isAvailable(variants)
        );
    }

    private CatalogProductDetailResponse toDetail(Product product, CatalogHydration hydration) {
        List<ProductImage> images = hydration.imagesByProductId().getOrDefault(product.getId(), List.of());
        List<ProductVariant> variants = hydration.variantsByProductId().getOrDefault(product.getId(), List.of());
        List<String> imageUrls = imageUrls(product, images);
        ProductPrice price = hydration.latestPriceByProductId().get(product.getId());
        BigDecimal discountedPrice = price == null ? null : calculateDiscountedPrice(product, price.getSellingPrice(), hydration);
        return new CatalogProductDetailResponse(
                product.getId(),
                product.getExternalId(),
                product.getArticleNumber(),
                product.getProductDisplayName(),
                product.getProductDisplayNameVi(),
                product.getVariantName(),
                product.getVariantNameVi(),
                product.getBrandName(),
                product.getAgeGroup(),
                product.getAgeGroupVi(),
                product.getGender(),
                product.getGenderVi(),
                product.getBaseColour(),
                product.getBaseColourVi(),
                product.getSeason(),
                product.getSeasonVi(),
                product.getYear(),
                product.getProductUsage(),
                product.getProductUsageVi(),
                product.getMaterial(),
                product.getMaterialVi(),
                product.getFit(),
                product.getFitVi(),
                product.getDescription(),
                product.getDescriptionVi(),
                toPrice(price, discountedPrice),
                imageUrls.isEmpty() ? null : imageUrls.getFirst(),
                imageUrls,
                toImages(product, images),
                toVariants(variants),
                toCategories(hydration.productCategoriesByProductId().getOrDefault(product.getId(), List.of())),
                toReviewSummary(hydration.reviewSummaryByProductId().get(product.getId())),
                totalStock(variants),
                isAvailable(variants),
                product.getCatalogAddDate(),
                product.getCreatedAt(),
                product.getUpdatedAt()
        );
    }

    private static CatalogProductPriceResponse toPrice(ProductPrice price, BigDecimal discountedPrice) {
        if (price == null) {
            return null;
        }
        BigDecimal effective = discountedPrice != null ? discountedPrice : price.getSellingPrice();
        return new CatalogProductPriceResponse(
                price.getSellingPrice(),
                discountedPrice,
                effective,
                price.getVat(),
                DEFAULT_CURRENCY
        );
    }

    private static List<CatalogProductImageResponse> toImages(Product product, List<ProductImage> images) {
        List<CatalogProductImageResponse> responses = new ArrayList<>();
        if (hasText(product.getMainImage())) {
            responses.add(new CatalogProductImageResponse(null, "MAIN", product.getMainImage(), 0));
        }

        for (ProductImage image : images) {
            if (!hasText(image.getImageUrl()) || containsImageUrl(responses, image.getImageUrl())) {
                continue;
            }
            responses.add(new CatalogProductImageResponse(
                    image.getId(),
                    image.getImageType(),
                    image.getImageUrl(),
                    image.getSortOrder()
            ));
        }

        return List.copyOf(responses);
    }

    private static List<CatalogProductVariantResponse> toVariants(List<ProductVariant> variants) {
        return variants.stream()
                .map(variant -> new CatalogProductVariantResponse(
                        variant.getId(),
                        variant.getSkuId(),
                        variant.getOptionName(),
                        variant.getOptionValue(),
                        variant.getUnifiedSize(),
                        variant.getInventoryCount(),
                        variant.getAvailable(),
                        variant.getActive()
                ))
                .toList();
    }

    private static List<CatalogCategoryResponse> toCategories(List<ProductCategory> productCategories) {
        Map<Long, CatalogCategoryResponse> categories = new LinkedHashMap<>();
        for (ProductCategory productCategory : productCategories) {
            Category category = productCategory.getCategory();
            if (category == null || !Boolean.TRUE.equals(category.getIsActive())) {
                continue;
            }
            categories.putIfAbsent(category.getId(), toCategory(category));
        }
        return List.copyOf(categories.values());
    }

    private static CatalogCategoryResponse toCategory(Category category) {
        return new CatalogCategoryResponse(
                category.getId(),
                category.getSourceCategoryId(),
                category.getCategoryLevel(),
                category.getCategoryName(),
                category.getCategoryNameVi(),
                category.getCanonicalCode(),
                category.getParentId()
        );
    }

    private static CatalogProductReviewSummaryResponse toReviewSummary(ProductReviewSummary summary) {
        if (summary == null) {
            return null;
        }
        return new CatalogProductReviewSummaryResponse(
                summary.getReviewCount(),
                summary.getApprovedReviewCount(),
                summary.getAverageRating(),
                summary.getRating1Count(),
                summary.getRating2Count(),
                summary.getRating3Count(),
                summary.getRating4Count(),
                summary.getRating5Count()
        );
    }

    private static Specification<Product> productSpecification(CatalogProductSearchRequest request, List<Long> categoryIds) {
        return (root, query, criteriaBuilder) -> {
            List<Predicate> predicates = new ArrayList<>();
            addKeywordPredicate(predicates, root, criteriaBuilder, request.keyword());
            addCaseInsensitiveEquals(predicates, root.get("gender"), criteriaBuilder, request.gender());
            addCaseInsensitiveEquals(predicates, root.get("brandName"), criteriaBuilder, request.brand());
            addCategoryPredicate(predicates, root, query, criteriaBuilder, categoryIds);
            addPricePredicate(predicates, root, query, criteriaBuilder, request.minPrice(), request.maxPrice());
            addAvailablePredicate(predicates, root, query, criteriaBuilder, request.available());
            return criteriaBuilder.and(predicates.toArray(Predicate[]::new));
        };
    }

    private static void addKeywordPredicate(
            List<Predicate> predicates,
            Root<Product> root,
            CriteriaBuilder criteriaBuilder,
            String keyword
    ) {
        if (!hasText(keyword)) {
            return;
        }

        String like = "%" + keyword.trim().toLowerCase(Locale.ROOT) + "%";
        predicates.add(criteriaBuilder.or(
                like(criteriaBuilder, root.get("productDisplayName"), like),
                like(criteriaBuilder, root.get("productDisplayNameVi"), like),
                like(criteriaBuilder, root.get("brandName"), like),
                like(criteriaBuilder, root.get("variantName"), like),
                like(criteriaBuilder, root.get("variantNameVi"), like),
                like(criteriaBuilder, root.get("baseColour"), like),
                like(criteriaBuilder, root.get("baseColourVi"), like),
                like(criteriaBuilder, root.get("gender"), like),
                like(criteriaBuilder, root.get("genderVi"), like),
                like(criteriaBuilder, root.get("material"), like),
                like(criteriaBuilder, root.get("materialVi"), like)
        ));
    }

    private static void addCaseInsensitiveEquals(
            List<Predicate> predicates,
            Path<String> path,
            CriteriaBuilder criteriaBuilder,
            String value
    ) {
        if (!hasText(value)) {
            return;
        }
        predicates.add(criteriaBuilder.equal(
                criteriaBuilder.lower(criteriaBuilder.coalesce(path, "")),
                value.trim().toLowerCase(Locale.ROOT)
        ));
    }

    private static void addCategoryPredicate(
            List<Predicate> predicates,
            Root<Product> root,
            CriteriaQuery<?> query,
            CriteriaBuilder criteriaBuilder,
            List<Long> categoryIds
    ) {
        if (categoryIds == null || categoryIds.isEmpty()) {
            return;
        }

        Subquery<Long> subquery = query.subquery(Long.class);
        Root<ProductCategory> productCategory = subquery.from(ProductCategory.class);
        subquery.select(productCategory.get("id"))
                .where(
                        criteriaBuilder.equal(productCategory.get("product").get("id"), root.get("id")),
                        productCategory.get("category").get("id").in(categoryIds)
                );
        predicates.add(criteriaBuilder.exists(subquery));
    }

    private static void addPricePredicate(
            List<Predicate> predicates,
            Root<Product> root,
            CriteriaQuery<?> query,
            CriteriaBuilder criteriaBuilder,
            BigDecimal minPrice,
            BigDecimal maxPrice
    ) {
        if (minPrice == null && maxPrice == null) {
            return;
        }

        Subquery<Long> subquery = query.subquery(Long.class);
        Root<ProductPrice> price = subquery.from(ProductPrice.class);
        Path<BigDecimal> sellingPrice = price.get("sellingPrice");

        List<Predicate> pricePredicates = new ArrayList<>();
        pricePredicates.add(criteriaBuilder.equal(price.get("product").get("id"), root.get("id")));
        if (minPrice != null) {
            pricePredicates.add(criteriaBuilder.greaterThanOrEqualTo(sellingPrice, minPrice));
        }
        if (maxPrice != null) {
            pricePredicates.add(criteriaBuilder.lessThanOrEqualTo(sellingPrice, maxPrice));
        }

        subquery.select(price.get("id"))
                .where(pricePredicates.toArray(Predicate[]::new));
        predicates.add(criteriaBuilder.exists(subquery));
    }

    private static void addAvailablePredicate(
            List<Predicate> predicates,
            Root<Product> root,
            CriteriaQuery<?> query,
            CriteriaBuilder criteriaBuilder,
            Boolean available
    ) {
        if (available == null) {
            return;
        }

        Subquery<Long> subquery = query.subquery(Long.class);
        Root<ProductVariant> variant = subquery.from(ProductVariant.class);
        subquery.select(variant.get("id"))
                .where(
                        criteriaBuilder.equal(variant.get("product").get("id"), root.get("id")),
                        criteriaBuilder.isTrue(variant.get("active")),
                        criteriaBuilder.isTrue(variant.get("available")),
                        criteriaBuilder.greaterThan(criteriaBuilder.coalesce(variant.get("inventoryCount"), 0), 0)
                );
        Predicate exists = criteriaBuilder.exists(subquery);
        predicates.add(Boolean.TRUE.equals(available) ? exists : criteriaBuilder.not(exists));
    }

    private static Predicate like(CriteriaBuilder criteriaBuilder, Path<String> path, String value) {
        return criteriaBuilder.like(criteriaBuilder.lower(criteriaBuilder.coalesce(path, "")), value);
    }

    private static ResolvedPageable resolvePageable(CatalogProductSearchRequest request) {
        int page = request.page() == null || request.page() < 0 ? 0 : request.page();
        int size = request.size() == null || request.size() <= 0 ? DEFAULT_PAGE_SIZE : request.size();
        size = Math.min(size, MAX_PAGE_SIZE);
        String sort = normalizeSort(request.sort());
        return new ResolvedPageable(PageRequest.of(page, size, sortFor(sort)), sort);
    }

    private static String normalizeSort(String sort) {
        if (!hasText(sort)) {
            return "newest";
        }
        String normalized = sort.trim().toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "newest", "oldest", "name_asc", "name_desc", "id_asc", "id_desc" -> normalized;
            default -> throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "unsupported_sort");
        };
    }

    private static Sort sortFor(String sort) {
        return switch (sort) {
            case "oldest" -> Sort.by(
                    Sort.Order.asc("catalogAddDate").nullsLast(),
                    Sort.Order.asc("createdAt").nullsLast(),
                    Sort.Order.asc("id")
            );
            case "name_asc" -> Sort.by(Sort.Order.asc("productDisplayName").ignoreCase(), Sort.Order.asc("id"));
            case "name_desc" -> Sort.by(Sort.Order.desc("productDisplayName").ignoreCase(), Sort.Order.desc("id"));
            case "id_asc" -> Sort.by(Sort.Order.asc("id"));
            case "id_desc" -> Sort.by(Sort.Order.desc("id"));
            default -> Sort.by(
                    Sort.Order.desc("catalogAddDate").nullsLast(),
                    Sort.Order.desc("createdAt").nullsLast(),
                    Sort.Order.desc("id")
            );
        };
    }

    private static void validatePriceRange(CatalogProductSearchRequest request) {
        if (request.minPrice() != null && request.maxPrice() != null
                && request.minPrice().compareTo(request.maxPrice()) > 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_price_range");
        }
    }

    private static CatalogProductSearchRequest emptyRequest() {
        return new CatalogProductSearchRequest(null, null, null, null, null, null, null, null, null, null);
    }

    private static List<String> imageUrls(Product product, List<ProductImage> images) {
        List<String> urls = new ArrayList<>();
        addImageUrl(urls, product.getMainImage());
        for (ProductImage image : images) {
            addImageUrl(urls, image.getImageUrl());
        }
        return List.copyOf(urls);
    }

    private static void addImageUrl(List<String> urls, String imageUrl) {
        if (hasText(imageUrl) && !urls.contains(imageUrl)) {
            urls.add(imageUrl);
        }
    }

    private static boolean containsImageUrl(List<CatalogProductImageResponse> images, String imageUrl) {
        return images.stream().anyMatch(image -> Objects.equals(image.imageUrl(), imageUrl));
    }

    private static BigDecimal effectivePrice(ProductPrice price) {
        if (price == null) {
            return null;
        }
        return price.getSellingPrice();
    }

    private static Integer totalStock(List<ProductVariant> variants) {
        return variants.stream()
                .filter(CatalogServiceImpl::isSellable)
                .map(ProductVariant::getInventoryCount)
                .filter(Objects::nonNull)
                .reduce(0, Integer::sum);
    }

    private static Boolean isAvailable(List<ProductVariant> variants) {
        return totalStock(variants) > 0;
    }

    private static boolean isSellable(ProductVariant variant) {
        return Boolean.TRUE.equals(variant.getActive())
                && Boolean.TRUE.equals(variant.getAvailable())
                && variant.getInventoryCount() != null
                && variant.getInventoryCount() > 0;
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

    private record CatalogHydration(
            Map<Long, List<ProductImage>> imagesByProductId,
            Map<Long, List<ProductCategory>> productCategoriesByProductId,
            Map<Long, List<ProductVariant>> variantsByProductId,
            Map<Long, ProductPrice> latestPriceByProductId,
            Map<Long, ProductReviewSummary> reviewSummaryByProductId,
            List<com.example.serviceapiecommerce.entity.Promotion> activePromotions,
            Map<Long, Set<Long>> promotionProductTargets,
            Map<Long, Set<Long>> promotionCategoryTargets
    ) {
    }

    private record ResolvedPageable(Pageable pageable, String sort) {
    }
}
