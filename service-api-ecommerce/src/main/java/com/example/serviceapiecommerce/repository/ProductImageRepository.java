package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ProductImage;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductImageRepository extends JpaRepository<ProductImage, Long> {
    Optional<ProductImage> findByIdAndProduct_Id(Long imageId, Long productId);

    void deleteByProduct_Id(Long productId);

    @Query("""
            select image
            from ProductImage image
            join fetch image.product product
            where product.id = :productId
            order by coalesce(image.sortOrder, 0), image.id
            """)
    List<ProductImage> findByProductIdOrderBySortOrder(@Param("productId") Long productId);

    @Query("""
            select image
            from ProductImage image
            join fetch image.product product
            where product.id in :productIds
            order by product.id, coalesce(image.sortOrder, 0), image.id
            """)
    List<ProductImage> findByProductIdInOrderByProductIdAndSortOrder(
            @Param("productIds") Collection<Long> productIds
    );
}
