package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ProductCategory;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductCategoryRepository extends JpaRepository<ProductCategory, Long> {
    Optional<ProductCategory> findByProduct_IdAndCategory_Id(Long productId, Long categoryId);

    void deleteByProduct_Id(Long productId);

    void deleteByProduct_IdAndCategory_Id(Long productId, Long categoryId);

    @Query("""
            select productCategory
            from ProductCategory productCategory
            join fetch productCategory.product product
            join fetch productCategory.category category
            where product.id = :productId
            order by category.categoryLevel, category.categoryName, category.id
            """)
    List<ProductCategory> findByProductIdWithCategory(@Param("productId") Long productId);

    @Query("""
            select productCategory
            from ProductCategory productCategory
            join fetch productCategory.product product
            join fetch productCategory.category category
            where product.id in :productIds
            order by product.id, category.categoryLevel, category.categoryName, category.id
            """)
    List<ProductCategory> findByProductIdInWithCategory(@Param("productIds") Collection<Long> productIds);
}
