package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Cart;
import com.example.serviceapiecommerce.entity.CartStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CartRepository extends JpaRepository<Cart, Long> {
    Optional<Cart> findFirstByUserAccount_IdAndStatusOrderByUpdatedAtDescIdDesc(
            Long userAccountId,
            CartStatus status
    );

    Optional<Cart> findByIdAndUserAccount_Id(Long cartId, Long userAccountId);

    List<Cart> findByUserAccount_IdOrderByUpdatedAtDescIdDesc(Long userAccountId);

    @Query("""
            select distinct cart
            from Cart cart
            left join fetch cart.items item
            left join fetch item.product product
            left join fetch item.productVariant variant
            where cart.id = :cartId
            """)
    Optional<Cart> findByIdWithItems(@Param("cartId") Long cartId);

    @Query("""
            select distinct cart
            from Cart cart
            left join fetch cart.items item
            left join fetch item.product product
            left join fetch item.productVariant variant
            where cart.userAccount.id = :userAccountId
              and cart.status = :status
            order by cart.updatedAt desc, cart.id desc
            """)
    List<Cart> findByUserAccountIdAndStatusWithItems(
            @Param("userAccountId") Long userAccountId,
            @Param("status") CartStatus status
    );
}
