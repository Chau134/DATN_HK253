package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.admin.AdminCategoryRequest;
import com.example.serviceapiecommerce.dto.admin.AdminCategoryResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductAttributeRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductAttributeResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductImageRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductImageResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductPriceRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductPriceResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductResponse;
import com.example.serviceapiecommerce.dto.admin.AdminProductVariantRequest;
import com.example.serviceapiecommerce.dto.admin.AdminProductVariantResponse;
import com.example.serviceapiecommerce.entity.Category;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductCategory;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.CategoryRepository;
import com.example.serviceapiecommerce.repository.ProductAttributeRepository;
import com.example.serviceapiecommerce.repository.ProductCategoryRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.service.AdminCatalogService;
import com.example.serviceapiecommerce.service.AiProductIndexHookService;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.Function;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AdminCatalogServiceImpl implements AdminCatalogService {
    private final ProductRepository productRepository;
    private final ProductVariantRepository productVariantRepository;
    private final ProductPriceRepository productPriceRepository;
    private final ProductImageRepository productImageRepository;
    private final ProductAttributeRepository productAttributeRepository;
    private final CategoryRepository categoryRepository;
    private final ProductCategoryRepository productCategoryRepository;
    private final AiProductIndexHookService aiProductIndexHookService;

    public AdminCatalogServiceImpl(
            ProductRepository productRepository,
            ProductVariantRepository productVariantRepository,
            ProductPriceRepository productPriceRepository,
            ProductImageRepository productImageRepository,
            ProductAttributeRepository productAttributeRepository,
            CategoryRepository categoryRepository,
            ProductCategoryRepository productCategoryRepository,
            AiProductIndexHookService aiProductIndexHookService
    ) {
        this.productRepository = productRepository;
        this.productVariantRepository = productVariantRepository;
        this.productPriceRepository = productPriceRepository;
        this.productImageRepository = productImageRepository;
        this.productAttributeRepository = productAttributeRepository;
        this.categoryRepository = categoryRepository;
        this.productCategoryRepository = productCategoryRepository;
        this.aiProductIndexHookService = aiProductIndexHookService;
    }

    @Override
    @Transactional(readOnly = true)
    public List<AdminCategoryResponse> listCategories(Boolean active) {
        List<Category> categories = active == null
                ? categoryRepository.findAll(Sort.by(Sort.Direction.ASC, "categoryLevel", "categoryName", "id"))
                : categoryRepository.findByIsActiveOrderByCategoryLevelAscCategoryNameAsc(active);
        return categories.stream()
                .map(AdminCatalogServiceImpl::toCategoryResponse)
                .toList();
    }

    @Override
    @Transactional
    public AdminCategoryResponse createCategory(AdminCategoryRequest request) {
        requireCategoryRequest(request);
        if (request.sourceCategoryId() != null && categoryRepository.findBySourceCategoryId(request.sourceCategoryId()).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "category_source_id_exists");
        }

        Category category = new Category();
        applyCategoryRequest(category, request, true);
        return toCategoryResponse(categoryRepository.save(category));
    }

    @Override
    @Transactional
    public AdminCategoryResponse updateCategory(Long categoryId, AdminCategoryRequest request) {
        requireCategoryRequest(request);
        Category category = category(categoryId);
        if (request.sourceCategoryId() != null) {
            categoryRepository.findBySourceCategoryId(request.sourceCategoryId())
                    .filter(existing -> !existing.getId().equals(category.getId()))
                    .ifPresent(existing -> {
                        throw new ResponseStatusException(HttpStatus.CONFLICT, "category_source_id_exists");
                    });
        }
        applyCategoryRequest(category, request, false);
        return toCategoryResponse(categoryRepository.save(category));
    }

    @Override
    @Transactional
    public void archiveCategory(Long categoryId) {
        Category category = category(categoryId);
        category.setIsActive(false);
        categoryRepository.save(category);
    }

    @Override
    @Transactional(readOnly = true)
    public List<AdminProductResponse> listProducts() {
        List<Product> products = productRepository.findAll(Sort.by(Sort.Direction.DESC, "updatedAt", "id"));
        AdminProductHydration hydration = hydrateProducts(products.stream().map(Product::getId).toList());
        return products.stream()
                .map(product -> toProductResponse(product, hydration))
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public AdminProductResponse getProduct(Long productId) {
        return toProductResponse(product(productId));
    }

    @Override
    @Transactional
    public AdminProductResponse createProduct(AdminProductRequest request) {
        requireProductRequest(request);
        Long productId = request.id() == null ? generatedProductId() : request.id();
        if (productRepository.existsById(productId)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "product_id_exists");
        }

        Instant now = Instant.now();
        Product product = new Product();
        product.setId(productId);
        applyProductRequest(product, request, now, true);
        Product savedProduct = productRepository.save(product);
        replaceProductCategories(savedProduct, request.categoryIds());
        return toProductResponse(savedProduct);
    }

    @Override
    @Transactional
    public AdminProductResponse updateProduct(Long productId, AdminProductRequest request) {
        requireProductRequest(request);
        Product product = product(productId);
        applyProductRequest(product, request, Instant.now(), false);
        Product savedProduct = productRepository.save(product);
        replaceProductCategories(savedProduct, request.categoryIds());
        return toProductResponse(savedProduct);
    }

    @Override
    @Transactional
    public void deleteProduct(Long productId) {
        Product product = product(productId);
        try {
            productCategoryRepository.deleteByProduct_Id(productId);
            productImageRepository.deleteByProduct_Id(productId);
            productAttributeRepository.deleteByProduct_Id(productId);
            productPriceRepository.deleteByProduct_Id(productId);
            productVariantRepository.deleteByProduct_Id(productId);
            productRepository.delete(product);
            productRepository.flush();
        } catch (DataIntegrityViolationException exception) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "product_in_use", exception);
        }
    }

    @Override
    @Transactional
    public AdminProductResponse addProductCategory(Long productId, Long categoryId) {
        Product product = product(productId);
        Category category = category(categoryId);
        productCategoryRepository.findByProduct_IdAndCategory_Id(productId, categoryId)
                .orElseGet(() -> {
                    ProductCategory productCategory = new ProductCategory();
                    productCategory.setProduct(product);
                    productCategory.setCategory(category);
                    return productCategoryRepository.save(productCategory);
                });
        syncProduct(productId);
        return toProductResponse(product);
    }

    @Override
    @Transactional
    public AdminProductResponse removeProductCategory(Long productId, Long categoryId) {
        product(productId);
        category(categoryId);
        productCategoryRepository.deleteByProduct_IdAndCategory_Id(productId, categoryId);
        syncProduct(productId);
        return toProductResponse(productRepository.getReferenceById(productId));
    }

    @Override
    @Transactional
    public AdminProductVariantResponse createVariant(Long productId, AdminProductVariantRequest request) {
        Product product = product(productId);
        Instant now = Instant.now();
        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        applyVariantRequest(variant, request, now, true);
        return toVariantResponse(productVariantRepository.save(variant));
    }

    @Override
    @Transactional
    public AdminProductVariantResponse updateVariant(Long productId, Long variantId, AdminProductVariantRequest request) {
        ProductVariant variant = variant(productId, variantId);
        applyVariantRequest(variant, request, Instant.now(), false);
        return toVariantResponse(productVariantRepository.save(variant));
    }

    @Override
    @Transactional
    public void deleteVariant(Long productId, Long variantId) {
        ProductVariant variant = variant(productId, variantId);
        productVariantRepository.delete(variant);
        syncProduct(productId);
    }

    @Override
    @Transactional
    public AdminProductPriceResponse addPrice(Long productId, AdminProductPriceRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "price_request_required");
        }
        Instant now = Instant.now();
        ProductPrice price = new ProductPrice();
        price.setProduct(product(productId));
        price.setSellingPrice(request.sellingPrice());
        price.setImportPrice(request.importPrice());
        price.setVat(request.vat());
        price.setCreatedAt(now);
        price.setUpdatedAt(now);
        return toPriceResponse(productPriceRepository.save(price));
    }

    @Override
    @Transactional
    public AdminProductImageResponse addImage(Long productId, AdminProductImageRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "image_request_required");
        }
        Product product = product(productId);
        ProductImage image = new ProductImage();
        image.setProduct(product);
        image.setImageType(request.imageType().trim());
        image.setImageUrl(request.imageUrl().trim());
        image.setSortOrder(request.sortOrder() == null ? 0 : request.sortOrder());
        image.setCreatedAt(Instant.now());
        ProductImage savedImage = productImageRepository.save(image);
        syncProduct(productId);
        return toImageResponse(savedImage);
    }

    @Override
    @Transactional
    public void deleteImage(Long productId, Long imageId) {
        ProductImage image = productImageRepository.findByIdAndProduct_Id(imageId, productId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_image_not_found"));
        productImageRepository.delete(image);
        syncProduct(productId);
    }

    @Override
    @Transactional
    public AdminProductAttributeResponse addAttribute(Long productId, AdminProductAttributeRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_attribute_request_required");
        }
        Product product = product(productId);
        Instant now = Instant.now();
        ProductAttribute attribute = new ProductAttribute();
        attribute.setProduct(product);
        applyAttributeRequest(attribute, request, now, true);
        ProductAttribute savedAttribute = productAttributeRepository.save(attribute);
        syncProduct(productId);
        return toAttributeResponse(savedAttribute);
    }

    @Override
    @Transactional
    public AdminProductAttributeResponse updateAttribute(Long productId, Long attributeId, AdminProductAttributeRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_attribute_request_required");
        }
        ProductAttribute attribute = attribute(productId, attributeId);
        applyAttributeRequest(attribute, request, Instant.now(), false);
        ProductAttribute savedAttribute = productAttributeRepository.save(attribute);
        syncProduct(productId);
        return toAttributeResponse(savedAttribute);
    }

    @Override
    @Transactional
    public void deleteAttribute(Long productId, Long attributeId) {
        ProductAttribute attribute = attribute(productId, attributeId);
        productAttributeRepository.delete(attribute);
        syncProduct(productId);
    }

    private void replaceProductCategories(Product product, List<Long> categoryIds) {
        Set<Long> uniqueIds = new LinkedHashSet<>(categoryIds == null ? List.of() : categoryIds);
        List<ProductCategory> existingCategories = productCategoryRepository.findByProductIdWithCategory(product.getId());
        for (ProductCategory existingCategory : existingCategories) {
            Long existingCategoryId = existingCategory.getCategory().getId();
            if (!uniqueIds.contains(existingCategoryId)) {
                productCategoryRepository.delete(existingCategory);
            }
        }
        for (Long categoryId : uniqueIds) {
            if (categoryId == null) {
                continue;
            }
            boolean alreadyLinked = existingCategories.stream()
                    .anyMatch(existingCategory -> categoryId.equals(existingCategory.getCategory().getId()));
            if (alreadyLinked) {
                continue;
            }
            ProductCategory productCategory = new ProductCategory();
            productCategory.setProduct(product);
            productCategory.setCategory(category(categoryId));
            productCategoryRepository.save(productCategory);
        }
        syncProduct(product.getId());
    }

    private Product product(Long productId) {
        if (productId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_id_required");
        }
        return productRepository.findById(productId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_not_found"));
    }

    private Category category(Long categoryId) {
        if (categoryId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "category_id_required");
        }
        return categoryRepository.findById(categoryId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "category_not_found"));
    }

    private ProductVariant variant(Long productId, Long variantId) {
        if (variantId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_variant_id_required");
        }
        return productVariantRepository.findByIdAndProduct_Id(variantId, productId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_variant_not_found"));
    }

    private ProductAttribute attribute(Long productId, Long attributeId) {
        if (attributeId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_attribute_id_required");
        }
        ProductAttribute attribute = productAttributeRepository.findById(attributeId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_attribute_not_found"));
        if (!attribute.getProduct().getId().equals(productId)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "product_attribute_mismatch");
        }
        return attribute;
    }

    private void applyCategoryRequest(Category category, AdminCategoryRequest request, boolean creating) {
        validateCategoryParent(category, request.parentId());
        String canonicalCode = canonicalCodeFromName(request.name());
        validateCategoryCanonicalCode(category, canonicalCode);
        category.setSourceCategoryId(request.sourceCategoryId());
        category.setCategoryLevel(request.level().trim());
        category.setCategoryName(request.name().trim());
        category.setCategoryNameVi(blankToNull(request.nameVi()));
        category.setParentId(request.parentId());
        category.setCanonicalCode(canonicalCode);
        category.setIsActive(request.active() == null ? (creating || Boolean.TRUE.equals(category.getIsActive())) : request.active());
    }

    private String canonicalCodeFromName(String name) {
        String canonicalCode = name.trim().toLowerCase(Locale.ROOT);
        if (canonicalCode.length() > 100) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "category_canonical_code_too_long");
        }
        return canonicalCode;
    }

    private void validateCategoryCanonicalCode(Category category, String canonicalCode) {
        categoryRepository.findByCanonicalCode(canonicalCode)
                .filter(existing -> !existing.getId().equals(category.getId()))
                .ifPresent(existing -> {
                    throw new ResponseStatusException(HttpStatus.CONFLICT, "category_canonical_code_exists");
                });
    }

    private void validateCategoryParent(Category category, Long parentId) {
        if (parentId == null) {
            return;
        }

        category(parentId);

        Long categoryId = category.getId();
        if (categoryId == null) {
            return;
        }

        if (categoryId.equals(parentId) || createsCategoryCycle(categoryId, parentId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "category_parent_cycle");
        }
    }

    private boolean createsCategoryCycle(Long categoryId, Long parentId) {
        Set<Long> visitedIds = new LinkedHashSet<>();
        Long currentParentId = parentId;
        while (currentParentId != null) {
            if (!visitedIds.add(currentParentId)) {
                return true;
            }
            if (categoryId.equals(currentParentId)) {
                return true;
            }
            currentParentId = category(currentParentId).getParentId();
        }
        return false;
    }

    private void applyProductRequest(Product product, AdminProductRequest request, Instant now, boolean creating) {
        product.setExternalId(request.externalId());
        product.setArticleNumber(blankToNull(request.articleNumber()));
        product.setProductDisplayName(request.title().trim());
        product.setProductDisplayNameVi(blankToNull(request.titleVi()));
        product.setVariantName(blankToNull(request.variantName()));
        product.setVariantNameVi(blankToNull(request.variantNameVi()));
        product.setBrandName(blankToNull(request.brand()));
        product.setAgeGroup(blankToNull(request.ageGroup()));
        product.setAgeGroupVi(blankToNull(request.ageGroupVi()));
        product.setGender(blankToNull(request.gender()));
        product.setGenderVi(blankToNull(request.genderVi()));
        product.setBaseColour(blankToNull(request.baseColour()));
        product.setBaseColourVi(blankToNull(request.baseColourVi()));
        product.setColour1(blankToNull(request.colour1()));
        product.setColour1Vi(blankToNull(request.colour1Vi()));
        product.setColour2(blankToNull(request.colour2()));
        product.setColour2Vi(blankToNull(request.colour2Vi()));
        product.setSeason(blankToNull(request.season()));
        product.setSeasonVi(blankToNull(request.seasonVi()));
        product.setYear(request.year());
        product.setProductUsage(blankToNull(request.usage()));
        product.setProductUsageVi(blankToNull(request.usageVi()));
        product.setMaterial(blankToNull(request.material()));
        product.setMaterialVi(blankToNull(request.materialVi()));
        product.setFit(blankToNull(request.fit()));
        product.setFitVi(blankToNull(request.fitVi()));
        product.setMainImage(blankToNull(request.mainImage()));
        product.setDescription(blankToNull(request.description()));
        product.setDescriptionVi(blankToNull(request.descriptionVi()));
        product.setCatalogAddDate(request.catalogAddDate() == null ? (creating ? now : product.getCatalogAddDate()) : request.catalogAddDate());
        if (creating) {
            product.setCreatedAt(now);
        }
        product.setUpdatedAt(now);
    }

    private static void applyVariantRequest(
            ProductVariant variant,
            AdminProductVariantRequest request,
            Instant now,
            boolean creating
    ) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_variant_request_required");
        }
        variant.setSkuId(request.skuId());
        variant.setOptionName(blankToNull(request.optionName()));
        variant.setOptionValue(blankToNull(request.optionValue()));
        variant.setUnifiedSize(blankToNull(request.unifiedSize()));
        variant.setInventoryCount(request.inventoryCount() == null ? (creating ? 0 : variant.getInventoryCount()) : request.inventoryCount());
        variant.setAvailable(request.available() == null ? (creating ? false : variant.getAvailable()) : request.available());
        variant.setActive(request.active() == null ? (creating || Boolean.TRUE.equals(variant.getActive())) : request.active());
        if (creating) {
            variant.setCreatedAt(now);
        }
        variant.setUpdatedAt(now);
    }

    private static void applyAttributeRequest(
            ProductAttribute attribute,
            AdminProductAttributeRequest request,
            Instant now,
            boolean creating
    ) {
        attribute.setAttrKey(request.attrKey().trim());
        attribute.setAttrValue(blankToNull(request.attrValue()));
        attribute.setAttrValueVi(blankToNull(request.attrValueVi()));
        if (creating) {
            attribute.setCreatedAt(now);
        }
        attribute.setUpdatedAt(now);
    }

    private AdminProductResponse toProductResponse(Product product) {
        return toProductResponse(product, hydrateProducts(List.of(product.getId())));
    }

    private AdminProductResponse toProductResponse(Product product, AdminProductHydration hydration) {
        Long productId = product.getId();
        List<Long> categoryIds = hydration.categoriesByProductId().getOrDefault(productId, List.of()).stream()
                .map(productCategory -> productCategory.getCategory().getId())
                .toList();
        return new AdminProductResponse(
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
                product.getColour1(),
                product.getColour1Vi(),
                product.getColour2(),
                product.getColour2Vi(),
                product.getSeason(),
                product.getSeasonVi(),
                product.getYear(),
                product.getProductUsage(),
                product.getProductUsageVi(),
                product.getMaterial(),
                product.getMaterialVi(),
                product.getFit(),
                product.getFitVi(),
                product.getMainImage(),
                product.getDescription(),
                product.getDescriptionVi(),
                product.getCatalogAddDate(),
                categoryIds,
                hydration.variantsByProductId().getOrDefault(productId, List.of()).stream()
                        .map(AdminCatalogServiceImpl::toVariantResponse)
                        .toList(),
                hydration.pricesByProductId().getOrDefault(productId, List.of()).stream()
                        .map(AdminCatalogServiceImpl::toPriceResponse)
                        .toList(),
                hydration.imagesByProductId().getOrDefault(productId, List.of()).stream()
                        .map(AdminCatalogServiceImpl::toImageResponse)
                        .toList(),
                hydration.attributesByProductId().getOrDefault(productId, List.of()).stream()
                        .map(AdminCatalogServiceImpl::toAttributeResponse)
                        .toList(),
                product.getCreatedAt(),
                product.getUpdatedAt()
        );
    }

    private AdminProductHydration hydrateProducts(List<Long> productIds) {
        if (productIds.isEmpty()) {
            return AdminProductHydration.empty();
        }
        return new AdminProductHydration(
                groupByProductId(
                        productCategoryRepository.findByProductIdInWithCategory(productIds),
                        productCategory -> productCategory.getProduct().getId()
                ),
                groupByProductId(
                        productVariantRepository.findByProductIdIn(productIds),
                        variant -> variant.getProduct().getId()
                ),
                groupByProductId(
                        productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds),
                        price -> price.getProduct().getId()
                ),
                groupByProductId(
                        productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds),
                        image -> image.getProduct().getId()
                ),
                groupByProductId(
                        productAttributeRepository.findByProductIdIn(productIds),
                        attribute -> attribute.getProduct().getId()
                )
        );
    }

    private static <T> Map<Long, List<T>> groupByProductId(
            Collection<T> values,
            Function<T, Long> productIdExtractor
    ) {
        Map<Long, List<T>> grouped = new LinkedHashMap<>();
        for (T value : values) {
            grouped.computeIfAbsent(productIdExtractor.apply(value), ignored -> new ArrayList<>()).add(value);
        }
        return grouped;
    }

    private static AdminCategoryResponse toCategoryResponse(Category category) {
        return new AdminCategoryResponse(
                category.getId(),
                category.getSourceCategoryId(),
                category.getCategoryLevel(),
                category.getCategoryName(),
                category.getCategoryNameVi(),
                category.getCanonicalCode(),
                category.getIsActive(),
                category.getParentId()
        );
    }

    private static AdminProductVariantResponse toVariantResponse(ProductVariant variant) {
        return new AdminProductVariantResponse(
                variant.getId(),
                variant.getProduct().getId(),
                variant.getSkuId(),
                variant.getOptionName(),
                variant.getOptionValue(),
                variant.getUnifiedSize(),
                variant.getInventoryCount(),
                variant.getAvailable(),
                variant.getActive(),
                variant.getCreatedAt(),
                variant.getUpdatedAt()
        );
    }

    private static AdminProductPriceResponse toPriceResponse(ProductPrice price) {
        return new AdminProductPriceResponse(
                price.getId(),
                price.getProduct().getId(),
                price.getSellingPrice(),
                price.getImportPrice(),
                price.getVat(),
                price.getCreatedAt(),
                price.getUpdatedAt()
        );
    }

    private static AdminProductImageResponse toImageResponse(ProductImage image) {
        return new AdminProductImageResponse(
                image.getId(),
                image.getProduct().getId(),
                image.getImageType(),
                image.getImageUrl(),
                image.getSortOrder(),
                image.getCreatedAt()
        );
    }

    private static AdminProductAttributeResponse toAttributeResponse(ProductAttribute attribute) {
        return new AdminProductAttributeResponse(
                attribute.getId(),
                attribute.getProduct().getId(),
                attribute.getAttrKey(),
                attribute.getAttrValue(),
                attribute.getAttrValueVi(),
                attribute.getCreatedAt(),
                attribute.getUpdatedAt()
        );
    }

    private void syncProduct(Long productId) {
        aiProductIndexHookService.syncProductAfterCommit(productId);
    }

    private Long generatedProductId() {
        for (int attempt = 0; attempt < 20; attempt++) {
            Long candidate = ThreadLocalRandom.current().nextLong(100_000_000L, 900_000_000L);
            if (!productRepository.existsById(candidate)) {
                return candidate;
            }
        }
        throw new ResponseStatusException(HttpStatus.CONFLICT, "product_id_generation_failed");
    }

    private static void requireCategoryRequest(AdminCategoryRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "category_request_required");
        }
    }

    private static void requireProductRequest(AdminProductRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_request_required");
        }
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private record AdminProductHydration(
            Map<Long, List<ProductCategory>> categoriesByProductId,
            Map<Long, List<ProductVariant>> variantsByProductId,
            Map<Long, List<ProductPrice>> pricesByProductId,
            Map<Long, List<ProductImage>> imagesByProductId,
            Map<Long, List<ProductAttribute>> attributesByProductId
    ) {
        private static AdminProductHydration empty() {
            return new AdminProductHydration(Map.of(), Map.of(), Map.of(), Map.of(), Map.of());
        }
    }
}
