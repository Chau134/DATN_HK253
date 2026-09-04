package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.CartItem;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CartItemRepository extends JpaRepository<CartItem, Long> {
    List<CartItem> findByCart_IdOrderByCreatedAtAscIdAsc(Long cartId);

    Optional<CartItem> findByCart_IdAndProductVariant_Id(Long cartId, Long productVariantId);

    Optional<CartItem> findByIdAndCart_UserAccount_Id(Long cartItemId, Long userAccountId);

    long deleteByCart_Id(Long cartId);

    @Query("""
            select item
            from CartItem item
            join fetch item.cart cart
            join fetch item.product product
            join fetch item.productVariant variant
            where cart.id = :cartId
            order by item.createdAt, item.id
            """)
    List<CartItem> findByCartIdWithProductData(@Param("cartId") Long cartId);
}
