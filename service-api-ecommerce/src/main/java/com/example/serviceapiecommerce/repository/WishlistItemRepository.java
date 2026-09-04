package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.WishlistItem;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WishlistItemRepository extends JpaRepository<WishlistItem, Long> {
    Optional<WishlistItem> findByWishlist_IdAndProduct_Id(Long wishlistId, Long productId);

    Optional<WishlistItem> findByIdAndWishlist_UserAccount_Id(Long wishlistItemId, Long userAccountId);

    boolean existsByWishlist_IdAndProduct_Id(Long wishlistId, Long productId);

    @EntityGraph(attributePaths = {"wishlist", "product", "productVariant"})
    List<WishlistItem> findByWishlist_IdOrderByCreatedAtDescIdDesc(Long wishlistId);

    @EntityGraph(attributePaths = {"wishlist", "product", "productVariant"})
    List<WishlistItem> findByWishlist_IdInOrderByCreatedAtDescIdDesc(Collection<Long> wishlistIds);

    @EntityGraph(attributePaths = {"wishlist", "product", "productVariant"})
    List<WishlistItem> findByWishlist_UserAccount_IdOrderByCreatedAtDescIdDesc(Long userAccountId);
}
