package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Wishlist;
import com.example.serviceapiecommerce.entity.WishlistStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WishlistRepository extends JpaRepository<Wishlist, Long> {
    Optional<Wishlist> findByUserAccount_IdAndName(Long userAccountId, String name);

    Optional<Wishlist> findByIdAndUserAccount_Id(Long wishlistId, Long userAccountId);

    boolean existsByUserAccount_IdAndName(Long userAccountId, String name);

    List<Wishlist> findByUserAccount_IdAndStatusOrderByUpdatedAtDescIdDesc(
            Long userAccountId,
            WishlistStatus status
    );
}
