package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.OrderItem;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OrderItemRepository extends JpaRepository<OrderItem, Long> {
    List<OrderItem> findByOrder_IdOrderByIdAsc(Long orderId);

    @Query("""
            select item
            from OrderItem item
            join fetch item.order customerOrder
            join fetch customerOrder.userAccount userAccount
            left join fetch item.product product
            left join fetch item.productVariant variant
            where item.id = :orderItemId
            """)
    Optional<OrderItem> findByIdWithReviewContext(@Param("orderItemId") Long orderItemId);

    @Query("""
            select item
            from OrderItem item
            left join fetch item.product product
            left join fetch item.productVariant variant
            where item.order.id = :orderId
            order by item.id
            """)
    List<OrderItem> findByOrderIdWithProductData(@Param("orderId") Long orderId);
}
