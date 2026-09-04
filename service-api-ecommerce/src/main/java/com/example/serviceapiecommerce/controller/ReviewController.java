package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.review.ProductReviewCreateRequest;
import com.example.serviceapiecommerce.dto.review.ProductReviewResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.ReviewService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/reviews")
public class ReviewController {
    private final ReviewService reviewService;

    public ReviewController(ReviewService reviewService) {
        this.reviewService = reviewService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ProductReviewResponse createReview(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @Valid @RequestBody ProductReviewCreateRequest request
    ) {
        return reviewService.createReview(currentUser.id(), request);
    }

    @GetMapping("/me")
    public List<ProductReviewResponse> myReviews(@AuthenticationPrincipal AuthenticatedUser currentUser) {
        return reviewService.listMyReviews(currentUser.id());
    }

    @GetMapping("/recent")
    public List<ProductReviewResponse> recentReviews(@RequestParam(defaultValue = "6") int limit) {
        return reviewService.listRecentReviews(limit);
    }
}
