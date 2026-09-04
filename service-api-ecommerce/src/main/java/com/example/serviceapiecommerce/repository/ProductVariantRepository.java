package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ProductVariant;
import jakarta.persistence.LockModeType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductVariantRepository extends JpaRepository<ProductVariant, Long> {
    void deleteByProduct_Id(Long productId);

    @Query("""
            select variant
            from ProductVariant variant
            join fetch variant.product product
            where variant.id = :variantId
            """)
    Optional<ProductVariant> findByIdWithProduct(@Param("variantId") Long variantId);

    Optional<ProductVariant> findByIdAndProduct_Id(Long variantId, Long productId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select variant
            from ProductVariant variant
            join fetch variant.product product
            where variant.id = :variantId
            """)
    Optional<ProductVariant> findByIdForUpdate(@Param("variantId") Long variantId);

    @Query("""
            select variant
            from ProductVariant variant
            join fetch variant.product product
            where product.id = :productId
            order by variant.optionName, variant.optionValue, variant.unifiedSize, variant.id
            """)
    List<ProductVariant> findByProductId(@Param("productId") Long productId);

    @Query("""
            select variant
            from ProductVariant variant
            join fetch variant.product product
            where product.id in :productIds
            order by product.id, variant.optionName, variant.optionValue, variant.unifiedSize, variant.id
            """)
    List<ProductVariant> findByProductIdIn(@Param("productIds") Collection<Long> productIds);
}
