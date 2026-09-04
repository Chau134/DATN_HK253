package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Category;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CategoryRepository extends JpaRepository<Category, Long> {
    List<Category> findByIsActiveTrueOrderByCategoryLevelAscCategoryNameAsc();

    List<Category> findByIsActiveOrderByCategoryLevelAscCategoryNameAsc(Boolean active);

    Optional<Category> findBySourceCategoryId(Long sourceCategoryId);

    Optional<Category> findByCanonicalCode(String canonicalCode);

    @Query("""
            select category
            from ProductCategory productCategory
            join productCategory.category category
            where productCategory.product.id = :productId
            order by category.categoryLevel, category.categoryName, category.id
            """)
    List<Category> findByProductId(@Param("productId") Long productId);

    @Query("""
            select category
            from ProductCategory productCategory
            join productCategory.category category
            where productCategory.product.id in :productIds
            order by productCategory.product.id, category.categoryLevel, category.categoryName, category.id
            """)
    List<Category> findByProductIdIn(@Param("productIds") Collection<Long> productIds);
}
