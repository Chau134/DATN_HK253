package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.review.ProductReviewResponse;
import com.example.serviceapiecommerce.dto.review.ProductReviewSummaryResponse;
import com.example.serviceapiecommerce.service.ReviewService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/products/{productId}/reviews")
public class ProductReviewController {
    private final ReviewService reviewService;

    public ProductReviewController(ReviewService reviewService) {
        this.reviewService = reviewService;
    }

    @GetMapping
    public List<ProductReviewResponse> productReviews(@PathVariable Long productId) {
        return reviewService.listApprovedProductReviews(productId);
    }

    @GetMapping("/summary")
    public ProductReviewSummaryResponse productReviewSummary(@PathVariable Long productId) {
        return reviewService.getProductReviewSummary(productId);
    }
}
