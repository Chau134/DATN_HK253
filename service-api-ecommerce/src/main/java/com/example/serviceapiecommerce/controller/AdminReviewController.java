package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.review.ProductReviewModerationRequest;
import com.example.serviceapiecommerce.dto.review.ProductReviewResponse;
import com.example.serviceapiecommerce.entity.ProductReviewStatus;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.ReviewService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/reviews")
public class AdminReviewController {
    private final ReviewService reviewService;

    public AdminReviewController(ReviewService reviewService) {
        this.reviewService = reviewService;
    }

    @GetMapping
    public List<ProductReviewResponse> reviews(@RequestParam(required = false) ProductReviewStatus status) {
        return reviewService.listAdminReviews(status);
    }

    @PatchMapping("/{reviewId}/moderate")
    public ProductReviewResponse moderateReview(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long reviewId,
            @Valid @RequestBody ProductReviewModerationRequest request
    ) {
        return reviewService.moderateReview(currentUser.id(), reviewId, request);
    }
}
