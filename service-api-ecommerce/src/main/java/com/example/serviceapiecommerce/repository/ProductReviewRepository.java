package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ProductReview;
import com.example.serviceapiecommerce.entity.ProductReviewStatus;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductReviewRepository extends JpaRepository<ProductReview, Long> {
    @EntityGraph(attributePaths = {"product", "productVariant", "userAccount", "order", "orderItem", "moderatedByUserAccount"})
    List<ProductReview> findByStatus(ProductReviewStatus status, Pageable pageable);

    Optional<ProductReview> findByOrderItem_Id(Long orderItemId);

    boolean existsByOrderItem_Id(Long orderItemId);

    List<ProductReview> findByProduct_Id(Long productId);

    long countByProduct_IdAndStatus(Long productId, ProductReviewStatus status);

    @EntityGraph(attributePaths = {"product", "productVariant", "userAccount", "order", "orderItem", "moderatedByUserAccount"})
    List<ProductReview> findByProduct_IdAndStatusOrderByCreatedAtDescIdDesc(
            Long productId,
            ProductReviewStatus status
    );

    @EntityGraph(attributePaths = {"product", "productVariant", "userAccount", "order", "orderItem", "moderatedByUserAccount"})
    List<ProductReview> findByUserAccount_IdOrderByCreatedAtDescIdDesc(Long userAccountId);

    long countByOrder_Id(Long orderId);

    @Query("""
            select review.order.id as orderId, count(review.id) as reviewCount
            from ProductReview review
            where review.order.id in :orderIds
            group by review.order.id
            """)
    List<OrderReviewCount> countByOrderIds(@Param("orderIds") Collection<Long> orderIds);

    @Query("""
            select review.orderItem.id
            from ProductReview review
            where review.orderItem.id in :orderItemIds
            """)
    List<Long> findReviewedOrderItemIds(@Param("orderItemIds") Collection<Long> orderItemIds);

    @EntityGraph(attributePaths = {"product", "productVariant", "userAccount", "order", "orderItem", "moderatedByUserAccount"})
    List<ProductReview> findByStatusOrderByCreatedAtAscIdAsc(ProductReviewStatus status);

    @EntityGraph(attributePaths = {"product", "productVariant", "userAccount", "order", "orderItem", "moderatedByUserAccount"})
    List<ProductReview> findAllByOrderByCreatedAtDescIdDesc();

    interface OrderReviewCount {
        Long getOrderId();

        long getReviewCount();
    }
}
