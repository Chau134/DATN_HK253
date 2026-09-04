package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ProductPrice;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductPriceRepository extends JpaRepository<ProductPrice, Long> {
    Optional<ProductPrice> findFirstByProduct_IdOrderByUpdatedAtDescIdDesc(Long productId);

    void deleteByProduct_Id(Long productId);

    @Query("""
            select price
            from ProductPrice price
            join fetch price.product product
            where product.id = :productId
            order by price.updatedAt desc, price.id desc
            """)
    List<ProductPrice> findByProductIdOrderByLatest(@Param("productId") Long productId);

    @Query("""
            select price
            from ProductPrice price
            join fetch price.product product
            where product.id in :productIds
            order by product.id, price.updatedAt desc, price.id desc
            """)
    List<ProductPrice> findByProductIdInOrderByProductIdAndLatest(
            @Param("productIds") Collection<Long> productIds
    );
}
