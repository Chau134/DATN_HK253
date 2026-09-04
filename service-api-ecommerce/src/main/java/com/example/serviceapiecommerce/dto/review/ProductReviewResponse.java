package com.example.serviceapiecommerce.dto.review;

import com.example.serviceapiecommerce.entity.ProductReviewStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

public record ProductReviewResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("product_id")
        Long productId,

        @JsonProperty("product_variant_id")
        Long productVariantId,

        @JsonProperty("user_account_id")
        Long userAccountId,

        @JsonProperty("order_id")
        Long orderId,

        @JsonProperty("order_item_id")
        Long orderItemId,

        @JsonProperty("rating")
        Integer rating,

        @JsonProperty("title")
        String title,

        @JsonProperty("content")
        String content,

        @JsonProperty("status")
        ProductReviewStatus status,

        @JsonProperty("verified_purchase")
        Boolean verifiedPurchase,

        @JsonProperty("helpful_count")
        Integer helpfulCount,

        @JsonProperty("reported_count")
        Integer reportedCount,

        @JsonProperty("moderation_reason")
        String moderationReason,

        @JsonProperty("moderated_by_user_account_id")
        Long moderatedByUserAccountId,

        @JsonProperty("moderated_at")
        Instant moderatedAt,

        @JsonProperty("created_at")
        Instant createdAt,

        @JsonProperty("updated_at")
        Instant updatedAt,

        @JsonProperty("user")
        ProductReviewUserResponse user,

        @JsonProperty("product_image_url")
        String productImageUrl,

        @JsonProperty("product_name")
        String productName
) {
}
