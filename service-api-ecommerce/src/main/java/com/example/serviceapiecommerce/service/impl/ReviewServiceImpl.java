package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.review.ProductReviewCreateRequest;
import com.example.serviceapiecommerce.dto.review.ProductReviewModerationRequest;
import com.example.serviceapiecommerce.dto.review.ProductReviewResponse;
import com.example.serviceapiecommerce.dto.review.ProductReviewSummaryResponse;
import com.example.serviceapiecommerce.dto.review.ProductReviewUserResponse;
import com.example.serviceapiecommerce.entity.CustomerProfile;
import com.example.serviceapiecommerce.entity.OrderItem;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductReview;
import com.example.serviceapiecommerce.entity.ProductReviewStatus;
import com.example.serviceapiecommerce.entity.ProductReviewSummary;
import com.example.serviceapiecommerce.repository.CustomerProfileRepository;
import com.example.serviceapiecommerce.repository.OrderItemRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductReviewRepository;
import com.example.serviceapiecommerce.repository.ProductReviewSummaryRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.ReviewService;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class ReviewServiceImpl implements ReviewService {
    private static final BigDecimal ZERO_RATING = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
    private static final EnumSet<OrderStatus> REVIEWABLE_ORDER_STATUSES = EnumSet.of(
            OrderStatus.PAID,
            OrderStatus.PACKING,
            OrderStatus.SHIPPING,
            OrderStatus.DELIVERED,
            OrderStatus.COMPLETED
    );
    private static final EnumSet<ProductReviewStatus> MODERATION_STATUSES = EnumSet.of(
            ProductReviewStatus.APPROVED,
            ProductReviewStatus.REJECTED,
            ProductReviewStatus.HIDDEN
    );

    private final ProductReviewRepository productReviewRepository;
    private final ProductReviewSummaryRepository productReviewSummaryRepository;
    private final OrderItemRepository orderItemRepository;
    private final ProductRepository productRepository;
    private final UserAccountRepository userAccountRepository;
    private final CustomerProfileRepository customerProfileRepository;

    public ReviewServiceImpl(
            ProductReviewRepository productReviewRepository,
            ProductReviewSummaryRepository productReviewSummaryRepository,
            OrderItemRepository orderItemRepository,
            ProductRepository productRepository,
            UserAccountRepository userAccountRepository,
            CustomerProfileRepository customerProfileRepository
    ) {
        this.productReviewRepository = productReviewRepository;
        this.productReviewSummaryRepository = productReviewSummaryRepository;
        this.orderItemRepository = orderItemRepository;
        this.productRepository = productRepository;
        this.userAccountRepository = userAccountRepository;
        this.customerProfileRepository = customerProfileRepository;
    }

    @Override
    @Transactional
    public ProductReviewResponse createReview(Long userAccountId, ProductReviewCreateRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "review_request_required");
        }
        OrderItem orderItem = orderItemRepository.findByIdWithReviewContext(request.orderItemId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order_item_not_found"));
        if (!orderItem.getOrder().getUserAccount().getId().equals(userAccountId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "order_item_not_found");
        }
        if (!REVIEWABLE_ORDER_STATUSES.contains(orderItem.getOrder().getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_item_not_reviewable");
        }
        if (orderItem.getProduct() == null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_item_product_missing");
        }
        if (productReviewRepository.existsByOrderItem_Id(orderItem.getId())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_item_already_reviewed");
        }

        Instant now = Instant.now();
        ProductReview review = new ProductReview();
        review.setProduct(orderItem.getProduct());
        review.setProductVariant(orderItem.getProductVariant());
        review.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
        review.setOrder(orderItem.getOrder());
        review.setOrderItem(orderItem);
        review.setRating(request.rating());
        review.setTitle(blankToNull(request.title()));
        review.setContent(blankToNull(request.content()));
        review.setStatus(ProductReviewStatus.APPROVED);
        review.setVerifiedPurchase(true);
        review.setHelpfulCount(0);
        review.setReportedCount(0);
        review.setCreatedAt(now);
        review.setUpdatedAt(now);

        ProductReview savedReview = productReviewRepository.save(review);
        recalculateSummary(orderItem.getProduct().getId(), now);
        return toResponse(savedReview);
    }

    @Override
    @Transactional(readOnly = true)
    public List<ProductReviewResponse> listMyReviews(Long userAccountId) {
        return toResponses(productReviewRepository.findByUserAccount_IdOrderByCreatedAtDescIdDesc(userAccountId));
    }

    @Override
    @Transactional(readOnly = true)
    public List<ProductReviewResponse> listApprovedProductReviews(Long productId) {
        requireExistingProduct(productId);
        return toResponses(productReviewRepository
                .findByProduct_IdAndStatusOrderByCreatedAtDescIdDesc(productId, ProductReviewStatus.APPROVED));
    }

    @Override
    @Transactional(readOnly = true)
    public List<ProductReviewResponse> listRecentReviews(int limit) {
        org.springframework.data.domain.PageRequest pageRequest = org.springframework.data.domain.PageRequest.of(
                0,
                limit,
                Sort.by(Sort.Direction.DESC, "createdAt", "id")
        );
        return toResponses(productReviewRepository.findByStatus(ProductReviewStatus.APPROVED, pageRequest));
    }

    @Override
    @Transactional(readOnly = true)
    public ProductReviewSummaryResponse getProductReviewSummary(Long productId) {
        requireExistingProduct(productId);
        return productReviewSummaryRepository.findByProduct_Id(productId)
                .map(ReviewServiceImpl::toSummaryResponse)
                .orElseGet(() -> emptySummary(productId));
    }

    @Override
    @Transactional(readOnly = true)
    public List<ProductReviewResponse> listAdminReviews(ProductReviewStatus status) {
        List<ProductReview> reviews = status == null
                ? productReviewRepository.findAllByOrderByCreatedAtDescIdDesc()
                : productReviewRepository.findByStatusOrderByCreatedAtAscIdAsc(status);
        return toResponses(reviews);
    }

    @Override
    @Transactional
    public ProductReviewResponse moderateReview(
            Long adminUserAccountId,
            Long reviewId,
            ProductReviewModerationRequest request
    ) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "review_moderation_request_required");
        }
        if (!MODERATION_STATUSES.contains(request.status())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "review_moderation_status_invalid");
        }

        ProductReview review = review(reviewId);
        Instant now = Instant.now();
        review.setStatus(request.status());
        review.setModerationReason(blankToNull(request.moderationReason()));
        review.setModeratedByUserAccount(userAccountRepository.getReferenceById(adminUserAccountId));
        review.setModeratedAt(now);
        review.setUpdatedAt(now);
        ProductReview savedReview = productReviewRepository.save(review);
        recalculateSummary(review.getProduct().getId(), now);
        return toResponse(savedReview);
    }

    private ProductReview review(Long reviewId) {
        if (reviewId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "review_id_required");
        }
        return productReviewRepository.findById(reviewId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "review_not_found"));
    }

    private void requireExistingProduct(Long productId) {
        if (productId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_id_required");
        }
        if (!productRepository.existsById(productId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "product_not_found");
        }
    }

    private ProductReviewSummary recalculateSummary(Long productId, Instant now) {
        List<ProductReview> reviews = productReviewRepository.findByProduct_Id(productId);
        int reviewCount = reviews.size();
        int approvedReviewCount = 0;
        int rating1Count = 0;
        int rating2Count = 0;
        int rating3Count = 0;
        int rating4Count = 0;
        int rating5Count = 0;
        int ratingSum = 0;

        for (ProductReview review : reviews) {
            if (review.getStatus() != ProductReviewStatus.APPROVED) {
                continue;
            }
            approvedReviewCount++;
            int rating = review.getRating() == null ? 0 : review.getRating();
            ratingSum += rating;
            if (rating == 1) {
                rating1Count++;
            } else if (rating == 2) {
                rating2Count++;
            } else if (rating == 3) {
                rating3Count++;
            } else if (rating == 4) {
                rating4Count++;
            } else if (rating == 5) {
                rating5Count++;
            }
        }

        BigDecimal averageRating = approvedReviewCount == 0
                ? ZERO_RATING
                : BigDecimal.valueOf(ratingSum)
                        .divide(BigDecimal.valueOf(approvedReviewCount), 2, RoundingMode.HALF_UP);

        ProductReviewSummary summary = productReviewSummaryRepository.findByProduct_Id(productId)
                .orElseGet(() -> {
                    ProductReviewSummary newSummary = new ProductReviewSummary();
                    Product product = productRepository.findById(productId)
                            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_not_found"));
                    newSummary.setProduct(product);
                    return newSummary;
                });
        summary.setReviewCount(reviewCount);
        summary.setApprovedReviewCount(approvedReviewCount);
        summary.setAverageRating(averageRating);
        summary.setRating1Count(rating1Count);
        summary.setRating2Count(rating2Count);
        summary.setRating3Count(rating3Count);
        summary.setRating4Count(rating4Count);
        summary.setRating5Count(rating5Count);
        summary.setUpdatedAt(now);
        return productReviewSummaryRepository.save(summary);
    }

    private ProductReviewResponse toResponse(ProductReview review) {
        CustomerProfile profile = review.getUserAccount() == null
                ? null
                : customerProfileRepository.findByUserAccount_Id(review.getUserAccount().getId()).orElse(null);
        return toResponse(review, profile);
    }

    private List<ProductReviewResponse> toResponses(List<ProductReview> reviews) {
        if (reviews.isEmpty()) {
            return List.of();
        }
        List<Long> userAccountIds = reviews.stream()
                .map(ProductReview::getUserAccount)
                .filter(java.util.Objects::nonNull)
                .map(userAccount -> userAccount.getId())
                .distinct()
                .toList();
        Map<Long, CustomerProfile> profilesByUserId = new LinkedHashMap<>();
        if (!userAccountIds.isEmpty()) {
            for (CustomerProfile profile : customerProfileRepository.findByUserAccount_IdIn(userAccountIds)) {
                profilesByUserId.put(profile.getUserAccount().getId(), profile);
            }
        }
        return reviews.stream()
                .map(review -> toResponse(
                        review,
                        review.getUserAccount() == null ? null : profilesByUserId.get(review.getUserAccount().getId())
                ))
                .toList();
    }

    private ProductReviewResponse toResponse(ProductReview review, CustomerProfile profile) {
        ProductReviewUserResponse userResponse = null;
        if (review.getUserAccount() != null) {
            userResponse = new ProductReviewUserResponse(
                    review.getUserAccount().getDisplayName(),
                    review.getUserAccount().getFullName(),
                    review.getUserAccount().getEmail(),
                    profile == null ? null : profile.getAvatarUrl()
            );
        }
        return new ProductReviewResponse(
                review.getId(),
                review.getProduct() == null ? null : review.getProduct().getId(),
                review.getProductVariant() == null ? null : review.getProductVariant().getId(),
                review.getUserAccount() == null ? null : review.getUserAccount().getId(),
                review.getOrder() == null ? null : review.getOrder().getId(),
                review.getOrderItem() == null ? null : review.getOrderItem().getId(),
                review.getRating(),
                review.getTitle(),
                review.getContent(),
                review.getStatus(),
                review.getVerifiedPurchase(),
                review.getHelpfulCount(),
                review.getReportedCount(),
                review.getModerationReason(),
                review.getModeratedByUserAccount() == null ? null : review.getModeratedByUserAccount().getId(),
                review.getModeratedAt(),
                review.getCreatedAt(),
                review.getUpdatedAt(),
                userResponse,
                review.getProduct() == null ? null : review.getProduct().getMainImage(),
                review.getProduct() == null ? null : (review.getProduct().getProductDisplayNameVi() != null ? review.getProduct().getProductDisplayNameVi() : review.getProduct().getProductDisplayName())
        );
    }

    private static ProductReviewSummaryResponse toSummaryResponse(ProductReviewSummary summary) {
        return new ProductReviewSummaryResponse(
                summary.getProduct().getId(),
                summary.getReviewCount(),
                summary.getApprovedReviewCount(),
                summary.getAverageRating(),
                summary.getRating1Count(),
                summary.getRating2Count(),
                summary.getRating3Count(),
                summary.getRating4Count(),
                summary.getRating5Count(),
                summary.getUpdatedAt()
        );
    }

    private static ProductReviewSummaryResponse emptySummary(Long productId) {
        return new ProductReviewSummaryResponse(
                productId,
                0,
                0,
                ZERO_RATING,
                0,
                0,
                0,
                0,
                0,
                null
        );
    }

    private static String blankToNull(String value) {
        return hasText(value) ? value.trim() : null;
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
