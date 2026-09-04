package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ProductAttribute;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductAttributeRepository extends JpaRepository<ProductAttribute, Long> {
    void deleteByProduct_Id(Long productId);

    @Query("""
            select attr
            from ProductAttribute attr
            join fetch attr.product product
            where product.id = :productId
            order by attr.attrKey, attr.id
            """)
    List<ProductAttribute> findByProductId(@Param("productId") Long productId);

    @Query("""
            select attr
            from ProductAttribute attr
            join fetch attr.product product
            where product.id in :productIds
            order by product.id, attr.attrKey, attr.id
            """)
    List<ProductAttribute> findByProductIdIn(@Param("productIds") Collection<Long> productIds);

    Optional<ProductAttribute> findFirstByProduct_IdAndAttrKeyOrderByUpdatedAtDescIdDesc(
            Long productId,
            String attrKey
    );
}
