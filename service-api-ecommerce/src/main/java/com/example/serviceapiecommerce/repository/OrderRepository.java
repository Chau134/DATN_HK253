package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderStatus;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OrderRepository extends JpaRepository<Order, Long> {
    Optional<Order> findByOrderNumber(String orderNumber);

    boolean existsByOrderNumber(String orderNumber);

    Optional<Order> findByCart_Id(Long cartId);

    Optional<Order> findByCart_IdAndUserAccount_Id(Long cartId, Long userAccountId);

    Optional<Order> findByIdAndUserAccount_Id(Long orderId, Long userAccountId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select customerOrder
            from CustomerOrder customerOrder
            join fetch customerOrder.userAccount userAccount
            where customerOrder.id = :orderId
            """)
    Optional<Order> findByIdForUpdate(@Param("orderId") Long orderId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select customerOrder
            from CustomerOrder customerOrder
            join fetch customerOrder.userAccount userAccount
            where customerOrder.id = :orderId
              and userAccount.id = :userAccountId
            """)
    Optional<Order> findByIdAndUserAccountIdForUpdate(
            @Param("orderId") Long orderId,
            @Param("userAccountId") Long userAccountId
    );

    List<Order> findByUserAccount_IdOrderByCreatedAtDescIdDesc(Long userAccountId);

    List<Order> findByStatusOrderByCreatedAtDescIdDesc(OrderStatus status);

    @Query("""
            select distinct customerOrder
            from CustomerOrder customerOrder
            left join fetch customerOrder.items item
            left join fetch item.product product
            left join fetch item.productVariant variant
            where customerOrder.id = :orderId
            """)
    Optional<Order> findByIdWithItems(@Param("orderId") Long orderId);
}
