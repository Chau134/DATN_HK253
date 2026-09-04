package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.review.ProductReviewCreateRequest;
import com.example.serviceapiecommerce.dto.review.ProductReviewModerationRequest;
import com.example.serviceapiecommerce.dto.review.ProductReviewResponse;
import com.example.serviceapiecommerce.dto.review.ProductReviewSummaryResponse;
import com.example.serviceapiecommerce.entity.ProductReviewStatus;
import java.util.List;

public interface ReviewService {
    ProductReviewResponse createReview(Long userAccountId, ProductReviewCreateRequest request);

    List<ProductReviewResponse> listMyReviews(Long userAccountId);

    List<ProductReviewResponse> listApprovedProductReviews(Long productId);

    List<ProductReviewResponse> listRecentReviews(int limit);

    ProductReviewSummaryResponse getProductReviewSummary(Long productId);

    List<ProductReviewResponse> listAdminReviews(ProductReviewStatus status);

    ProductReviewResponse moderateReview(
            Long adminUserAccountId,
            Long reviewId,
            ProductReviewModerationRequest request
    );
}
