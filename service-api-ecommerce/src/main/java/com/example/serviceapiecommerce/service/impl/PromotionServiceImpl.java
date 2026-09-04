package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.promotion.AdminPromotionRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionCategoryRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionCategoryResponse;
import com.example.serviceapiecommerce.dto.promotion.PromotionProductRequest;
import com.example.serviceapiecommerce.dto.promotion.PromotionProductResponse;
import com.example.serviceapiecommerce.dto.promotion.PromotionResponse;
import com.example.serviceapiecommerce.entity.Category;
import com.example.serviceapiecommerce.entity.DiscountType;
import com.example.serviceapiecommerce.entity.OrderItem;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductCategory;
import com.example.serviceapiecommerce.entity.Promotion;
import com.example.serviceapiecommerce.entity.PromotionCategory;
import com.example.serviceapiecommerce.entity.PromotionCustomerScope;
import com.example.serviceapiecommerce.entity.PromotionProduct;
import com.example.serviceapiecommerce.entity.PromotionStatus;
import com.example.serviceapiecommerce.repository.CategoryRepository;
import com.example.serviceapiecommerce.repository.ProductCategoryRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.PromotionCategoryRepository;
import com.example.serviceapiecommerce.repository.PromotionProductRepository;
import com.example.serviceapiecommerce.repository.PromotionRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.PromotionService;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.Collection;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class PromotionServiceImpl implements PromotionService {
    private static final String DEFAULT_CURRENCY = "VND";
    private static final BigDecimal ZERO = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);

    private final PromotionRepository promotionRepository;
    private final PromotionProductRepository promotionProductRepository;
    private final PromotionCategoryRepository promotionCategoryRepository;
    private final ProductCategoryRepository productCategoryRepository;
    private final ProductRepository productRepository;
    private final CategoryRepository categoryRepository;
    private final UserAccountRepository userAccountRepository;

    public PromotionServiceImpl(
            PromotionRepository promotionRepository,
            PromotionProductRepository promotionProductRepository,
            PromotionCategoryRepository promotionCategoryRepository,
            ProductCategoryRepository productCategoryRepository,
            ProductRepository productRepository,
            CategoryRepository categoryRepository,
            UserAccountRepository userAccountRepository
    ) {
        this.promotionRepository = promotionRepository;
        this.promotionProductRepository = promotionProductRepository;
        this.promotionCategoryRepository = promotionCategoryRepository;
        this.productCategoryRepository = productCategoryRepository;
        this.productRepository = productRepository;
        this.categoryRepository = categoryRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @Override
    @Transactional
    public PromotionResponse createPromotion(AdminPromotionRequest request) {
        requireRequest(request);
        Instant now = Instant.now();
        Promotion promotion = new Promotion();
        applyRequest(promotion, request, now, true);
        promotion.setCreatedAt(now);
        promotion.setUpdatedAt(now);
        return toResponse(promotionRepository.save(promotion));
    }

    @Override
    @Transactional
    public PromotionResponse updatePromotion(Long promotionId, AdminPromotionRequest request) {
        requireRequest(request);
        Promotion promotion = promotion(promotionId);
        applyRequest(promotion, request, Instant.now(), false);
        return toResponse(promotionRepository.save(promotion));
    }

    @Override
    @Transactional(readOnly = true)
    public List<PromotionResponse> listPromotions(PromotionStatus status) {
        List<Promotion> promotions = status == null
                ? promotionRepository.findAll(Sort.by(Sort.Direction.DESC, "createdAt", "id"))
                : promotionRepository.findByStatusOrderByPriorityDescCreatedAtDescIdDesc(status);

        List<Long> promoIds = promotions.stream().map(Promotion::getId).toList();
        Map<Long, List<Long>> productsMap = new LinkedHashMap<>();
        Map<Long, List<Long>> categoriesMap = new LinkedHashMap<>();
        if (!promoIds.isEmpty()) {
            promotionProductRepository.findByPromotion_IdInAndActive(promoIds, true)
                .forEach(pp -> productsMap.computeIfAbsent(pp.getPromotion().getId(), k -> new java.util.ArrayList<>()).add(pp.getProduct().getId()));
            promotionCategoryRepository.findByPromotion_IdInAndActive(promoIds, true)
                .forEach(pc -> categoriesMap.computeIfAbsent(pc.getPromotion().getId(), k -> new java.util.ArrayList<>()).add(pc.getCategory().getId()));
        }

        return promotions.stream()
                .map(p -> toResponse(p, productsMap.getOrDefault(p.getId(), List.of()), categoriesMap.getOrDefault(p.getId(), List.of())))
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public PromotionResponse getPromotion(Long promotionId) {
        Promotion p = promotion(promotionId);
        List<Long> productIds = promotionProductRepository.findByPromotion_IdOrderByCreatedAtDescIdDesc(p.getId()).stream()
                .filter(pp -> Boolean.TRUE.equals(pp.getActive()))
                .map(pp -> pp.getProduct().getId())
                .toList();
        List<Long> categoryIds = promotionCategoryRepository.findByPromotion_IdOrderByCreatedAtDescIdDesc(p.getId()).stream()
                .filter(pc -> Boolean.TRUE.equals(pc.getActive()))
                .map(pc -> pc.getCategory().getId())
                .toList();
        return toResponse(p, productIds, categoryIds);
    }

    @Override
    @Transactional
    public void archivePromotion(Long promotionId) {
        Promotion promotion = promotion(promotionId);
        promotion.setStatus(PromotionStatus.ARCHIVED);
        promotion.setUpdatedAt(Instant.now());
        promotionRepository.save(promotion);
    }

    @Override
    @Transactional
    public PromotionProductResponse addPromotionProduct(Long promotionId, PromotionProductRequest request) {
        if (request == null || request.productId() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_id_required");
        }
        Promotion promotion = promotion(promotionId);
        Product product = productRepository.findById(request.productId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_not_found"));
        PromotionProduct target = promotionProductRepository
                .findByPromotion_IdAndProduct_Id(promotion.getId(), product.getId())
                .orElseGet(PromotionProduct::new);
        if (target.getId() == null) {
            target.setPromotion(promotion);
            target.setProduct(product);
            target.setCreatedAt(Instant.now());
        }
        target.setActive(request.active() == null || request.active());
        return toProductResponse(promotionProductRepository.save(target));
    }

    @Override
    @Transactional
    public void removePromotionProduct(Long promotionId, Long productId) {
        if (promotionId == null || productId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "promotion_product_target_required");
        }
        promotionProductRepository.findByPromotion_IdAndProduct_Id(promotionId, productId)
                .ifPresent(promotionProductRepository::delete);
    }

    @Override
    @Transactional
    public PromotionCategoryResponse addPromotionCategory(Long promotionId, PromotionCategoryRequest request) {
        if (request == null || request.categoryId() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "category_id_required");
        }
        Promotion promotion = promotion(promotionId);
        Category category = categoryRepository.findById(request.categoryId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "category_not_found"));
        PromotionCategory target = promotionCategoryRepository
                .findByPromotion_IdAndCategory_Id(promotion.getId(), category.getId())
                .orElseGet(PromotionCategory::new);
        if (target.getId() == null) {
            target.setPromotion(promotion);
            target.setCategory(category);
            target.setCreatedAt(Instant.now());
        }
        target.setActive(request.active() == null || request.active());
        return toCategoryResponse(promotionCategoryRepository.save(target));
    }

    @Override
    @Transactional
    public void removePromotionCategory(Long promotionId, Long categoryId) {
        if (promotionId == null || categoryId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "promotion_category_target_required");
        }
        promotionCategoryRepository.findByPromotion_IdAndCategory_Id(promotionId, categoryId)
                .ifPresent(promotionCategoryRepository::delete);
    }
    @Override
    @Transactional(readOnly = true)
    public List<PromotionProductResponse> listPromotionProducts(Long promotionId) {
        return promotionProductRepository.findByPromotion_IdOrderByCreatedAtDescIdDesc(promotionId).stream()
                .map(PromotionServiceImpl::toProductResponse)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public List<PromotionCategoryResponse> listPromotionCategories(Long promotionId) {
        return promotionCategoryRepository.findByPromotion_IdOrderByCreatedAtDescIdDesc(promotionId).stream()
                .map(PromotionServiceImpl::toCategoryResponse)
                .toList();
    }

    @Override
    @Transactional
    public void clearPromotionTargets(Long promotionId) {
        Promotion promotion = promotion(promotionId);
        promotionProductRepository.deleteByPromotion_Id(promotion.getId());
        promotionCategoryRepository.deleteByPromotion_Id(promotion.getId());
    }

    @Override
    @Transactional(readOnly = true)
    public BigDecimal applyAutomaticPromotions(
            Long userAccountId,
            List<OrderItem> orderItems,
            BigDecimal subtotal,
            String currency,
            Instant now
    ) {
        if (orderItems == null || orderItems.isEmpty()) {
            return ZERO;
        }
        Instant resolvedNow = now == null ? Instant.now() : now;
        String resolvedCurrency = blankToDefault(currency, DEFAULT_CURRENCY);
        List<Promotion> candidates = promotionRepository.findByStatusOrderByPriorityDescCreatedAtDescIdDesc(
                PromotionStatus.ACTIVE
        );
        if (candidates.isEmpty()) {
            return ZERO;
        }

        List<Long> promotionIds = candidates.stream()
                .map(Promotion::getId)
                .toList();
        Map<Long, Set<Long>> productTargets = groupTargetIds(
                promotionProductRepository.findByPromotion_IdInAndActive(promotionIds, true),
                target -> target.getPromotion().getId(),
                target -> target.getProduct().getId()
        );
        Map<Long, Set<Long>> categoryTargets = groupTargetIds(
                promotionCategoryRepository.findByPromotion_IdInAndActive(promotionIds, true),
                target -> target.getPromotion().getId(),
                target -> target.getCategory().getId()
        );
        Map<Long, Set<Long>> categoryIdsByProductId = productCategoryIdsByProductId(orderItems);

        BigDecimal totalDiscount = ZERO;
        for (Promotion promotion : candidates) {
            if (!eligiblePromotion(promotion, userAccountId, money(subtotal), resolvedCurrency, resolvedNow)) {
                continue;
            }
            List<OrderItem> eligibleItems = eligibleItems(
                    promotion,
                    orderItems,
                    productTargets.getOrDefault(promotion.getId(), Set.of()),
                    categoryTargets.getOrDefault(promotion.getId(), Set.of()),
                    categoryIdsByProductId
            );
            BigDecimal eligibleAmount = eligibleItems.stream()
                    .map(item -> money(item.getLineTotal()))
                    .reduce(ZERO, BigDecimal::add);
            BigDecimal discount = calculateDiscount(promotion, eligibleAmount);
            BigDecimal applied = allocateDiscount(eligibleItems, discount);
            if (applied.compareTo(ZERO) <= 0) {
                continue;
            }
            totalDiscount = totalDiscount.add(applied);
            if (!Boolean.TRUE.equals(promotion.getStackable())) {
                break;
            }
        }
        return totalDiscount.setScale(2, RoundingMode.HALF_UP);
    }

    private boolean eligiblePromotion(
            Promotion promotion,
            Long userAccountId,
            BigDecimal subtotal,
            String currency,
            Instant now
    ) {
        if (promotion.getStartsAt() != null && promotion.getStartsAt().isAfter(now)) {
            return false;
        }
        if (promotion.getEndsAt() != null && !promotion.getEndsAt().isAfter(now)) {
            return false;
        }
        if (!blankToDefault(promotion.getCurrency(), DEFAULT_CURRENCY).equalsIgnoreCase(currency)) {
            return false;
        }
        if (subtotal.compareTo(money(promotion.getMinOrderAmount())) < 0) {
            return false;
        }
        return customerEligible(promotion, userAccountId);
    }

    private boolean customerEligible(Promotion promotion, Long userAccountId) {
        PromotionCustomerScope scope = promotion.getCustomerScope() == null
                ? PromotionCustomerScope.ALL
                : promotion.getCustomerScope();
        if (scope == PromotionCustomerScope.ALL) {
            return true;
        }
        if (scope == PromotionCustomerScope.SPECIFIC_CUSTOMER) {
            return promotion.getEligibleUserAccount() != null
                    && promotion.getEligibleUserAccount().getId().equals(userAccountId);
        }
        return false;
    }

    private List<OrderItem> eligibleItems(
            Promotion promotion,
            List<OrderItem> orderItems,
            Set<Long> productTargets,
            Set<Long> categoryTargets,
            Map<Long, Set<Long>> categoryIdsByProductId
    ) {
        if (promotion.getDiscountType() == DiscountType.FREE_SHIPPING) {
            return List.of();
        }
        if (productTargets.isEmpty() && categoryTargets.isEmpty()) {
            return orderItems;
        }
        return orderItems.stream()
                .filter(item -> {
                    Long productId = productId(item);
                    if (productId == null) {
                        return false;
                    }
                    if (productTargets.contains(productId)) {
                        return true;
                    }
                    Set<Long> itemCategoryIds = categoryIdsByProductId.getOrDefault(productId, Set.of());
                    return itemCategoryIds.stream().anyMatch(categoryTargets::contains);
                })
                .toList();
    }

    private BigDecimal allocateDiscount(List<OrderItem> items, BigDecimal discount) {
        BigDecimal remainingDiscount = money(discount);
        if (items.isEmpty() || remainingDiscount.compareTo(ZERO) <= 0) {
            return ZERO;
        }
        BigDecimal eligibleAmount = items.stream()
                .map(item -> money(item.getLineTotal()))
                .reduce(ZERO, BigDecimal::add);
        if (eligibleAmount.compareTo(ZERO) <= 0) {
            return ZERO;
        }

        BigDecimal applied = ZERO;
        for (int i = 0; i < items.size(); i++) {
            OrderItem item = items.get(i);
            BigDecimal lineTotal = money(item.getLineTotal());
            if (lineTotal.compareTo(ZERO) <= 0) {
                continue;
            }
            BigDecimal allocation = i == items.size() - 1
                    ? remainingDiscount
                    : remainingDiscount.multiply(lineTotal).divide(eligibleAmount, 2, RoundingMode.HALF_UP);
            allocation = allocation.min(lineTotal).min(remainingDiscount);
            if (allocation.compareTo(ZERO) <= 0) {
                continue;
            }
            item.setLineDiscount(money(item.getLineDiscount()).add(allocation));
            item.setLineTotal(lineTotal.subtract(allocation).max(ZERO));
            remainingDiscount = remainingDiscount.subtract(allocation);
            applied = applied.add(allocation);
        }
        return applied.setScale(2, RoundingMode.HALF_UP);
    }

    private Map<Long, Set<Long>> productCategoryIdsByProductId(List<OrderItem> orderItems) {
        List<Long> productIds = orderItems.stream()
                .map(PromotionServiceImpl::productId)
                .filter(id -> id != null)
                .distinct()
                .toList();
        if (productIds.isEmpty()) {
            return Map.of();
        }
        Map<Long, Set<Long>> categoryIds = new LinkedHashMap<>();
        for (ProductCategory productCategory : productCategoryRepository.findByProductIdInWithCategory(productIds)) {
            categoryIds.computeIfAbsent(productCategory.getProduct().getId(), ignored -> new HashSet<>())
                    .add(productCategory.getCategory().getId());
        }
        return categoryIds;
    }

    private void applyRequest(Promotion promotion, AdminPromotionRequest request, Instant now, boolean creating) {
        validateWindow(request.startsAt(), request.endsAt());
        promotion.setName(request.name().trim());
        promotion.setDescription(blankToNull(request.description()));
        promotion.setDiscountType(request.discountType());
        promotion.setDiscountValue(money(request.discountValue()));
        promotion.setMaxDiscountAmount(nullableMoney(request.maxDiscountAmount()));
        promotion.setMinOrderAmount(money(request.minOrderAmount()));
        promotion.setCurrency(blankToDefault(request.currency(), DEFAULT_CURRENCY).toUpperCase());
        promotion.setStatus(request.status() == null
                ? (creating ? PromotionStatus.ACTIVE : promotion.getStatus())
                : request.status());
        promotion.setPriority(request.priority() == null ? (creating ? 0 : promotion.getPriority()) : request.priority());
        promotion.setStackable(request.stackable() == null
                ? (!creating && Boolean.TRUE.equals(promotion.getStackable()))
                : request.stackable());
        promotion.setCustomerScope(request.customerScope() == null
                ? (creating ? PromotionCustomerScope.ALL : promotion.getCustomerScope())
                : request.customerScope());
        promotion.setEligibleUserAccount(request.eligibleUserAccountId() == null
                ? null
                : userAccountRepository.findById(request.eligibleUserAccountId())
                        .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "eligible_user_not_found")));
        promotion.setCustomerSegment(blankToNull(request.customerSegment()));
        promotion.setStartsAt(request.startsAt());
        promotion.setEndsAt(request.endsAt());
        promotion.setUpdatedAt(now);
    }

    private static BigDecimal calculateDiscount(Promotion promotion, BigDecimal eligibleAmount) {
        BigDecimal base = money(eligibleAmount);
        if (base.compareTo(ZERO) <= 0 || promotion.getDiscountType() == DiscountType.FREE_SHIPPING) {
            return ZERO;
        }
        BigDecimal discount;
        if (promotion.getDiscountType() == DiscountType.PERCENTAGE) {
            discount = base.multiply(money(promotion.getDiscountValue()))
                    .divide(BigDecimal.valueOf(100), 2, RoundingMode.HALF_UP);
        } else {
            discount = money(promotion.getDiscountValue());
        }
        if (promotion.getMaxDiscountAmount() != null) {
            discount = discount.min(money(promotion.getMaxDiscountAmount()));
        }
        return discount.min(base).max(ZERO).setScale(2, RoundingMode.HALF_UP);
    }

    private Promotion promotion(Long promotionId) {
        if (promotionId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "promotion_id_required");
        }
        return promotionRepository.findById(promotionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "promotion_not_found"));
    }

    private static PromotionResponse toResponse(Promotion promotion) {
        return toResponse(promotion, List.of(), List.of());
    }

    private static PromotionResponse toResponse(Promotion promotion, List<Long> productIds, List<Long> categoryIds) {
        return new PromotionResponse(
                promotion.getId(),
                promotion.getName(),
                promotion.getDescription(),
                promotion.getDiscountType(),
                promotion.getDiscountValue(),
                promotion.getMaxDiscountAmount(),
                promotion.getMinOrderAmount(),
                promotion.getCurrency(),
                promotion.getStatus(),
                promotion.getPriority(),
                promotion.getStackable(),
                promotion.getCustomerScope(),
                promotion.getEligibleUserAccount() == null ? null : promotion.getEligibleUserAccount().getId(),
                promotion.getCustomerSegment(),
                promotion.getStartsAt(),
                promotion.getEndsAt(),
                productIds,
                categoryIds,
                promotion.getCreatedAt(),
                promotion.getUpdatedAt()
        );
    }

    private static PromotionProductResponse toProductResponse(PromotionProduct target) {
        return new PromotionProductResponse(
                target.getId(),
                target.getPromotion().getId(),
                target.getProduct().getId(),
                target.getProduct().getProductDisplayName(),
                target.getActive(),
                target.getCreatedAt()
        );
    }

    private static PromotionCategoryResponse toCategoryResponse(PromotionCategory target) {
        return new PromotionCategoryResponse(
                target.getId(),
                target.getPromotion().getId(),
                target.getCategory().getId(),
                target.getCategory().getCategoryName(),
                target.getActive(),
                target.getCreatedAt()
        );
    }

    private static <T> Map<Long, Set<Long>> groupTargetIds(
            Collection<T> targets,
            Function<T, Long> promotionId,
            Function<T, Long> targetId
    ) {
        Map<Long, Set<Long>> grouped = new LinkedHashMap<>();
        for (T target : targets) {
            grouped.computeIfAbsent(promotionId.apply(target), ignored -> new HashSet<>())
                    .add(targetId.apply(target));
        }
        return grouped;
    }

    private static Long productId(OrderItem item) {
        if (item.getSourceProductId() != null) {
            return item.getSourceProductId();
        }
        return item.getProduct() == null ? null : item.getProduct().getId();
    }

    private static void requireRequest(AdminPromotionRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "promotion_request_required");
        }
    }

    private static void validateWindow(Instant startsAt, Instant endsAt) {
        if (startsAt != null && endsAt != null && !startsAt.isBefore(endsAt)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "promotion_invalid_time_window");
        }
    }

    private static BigDecimal nullableMoney(BigDecimal value) {
        return value == null ? null : money(value);
    }

    private static BigDecimal money(BigDecimal value) {
        return value == null ? ZERO : value.setScale(2, RoundingMode.HALF_UP);
    }

    private static String blankToDefault(String value, String defaultValue) {
        String resolved = blankToNull(value);
        return resolved == null ? defaultValue : resolved;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
