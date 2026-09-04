package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Product;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ProductRepository extends JpaRepository<Product, Long>, JpaSpecificationExecutor<Product> {
    @Query("""
            select distinct p.brandName
            from Product p
            where p.brandName is not null and p.brandName <> ''
            order by p.brandName asc
            """)
    List<String> findDistinctBrandNames();

    @Query("""
            select p
            from Product p
            where p.id = :productId
            """)
    Optional<Product> findForAiIndexingById(@Param("productId") Long productId);

    @Query("""
            select p
            from Product p
            where p.id in :productIds
            """)
    List<Product> findAllByIdInForAiIndexing(@Param("productIds") Collection<Long> productIds);

    @Query(
            value = """
                    select p
                    from Product p
                    where p.productDisplayName is not null
                       or p.productDisplayNameVi is not null
                       or p.description is not null
                       or p.descriptionVi is not null
                       or p.mainImage is not null
                    """,
            countQuery = """
                    select count(p)
                    from Product p
                    where p.productDisplayName is not null
                       or p.productDisplayNameVi is not null
                       or p.description is not null
                       or p.descriptionVi is not null
                       or p.mainImage is not null
                    """
    )
    Page<Product> findAllSearchableProducts(Pageable pageable);

    @Query("""
            select p
            from Product p
            where p.productDisplayName is not null
               or p.productDisplayNameVi is not null
               or p.description is not null
               or p.descriptionVi is not null
               or p.mainImage is not null
            order by p.id asc
            """)
    List<Product> findMockAiCandidates(Pageable pageable);

    @Query("""
            select distinct p
            from Product p
            where lower(p.productDisplayName) like concat('%', :keyword, '%')
               or lower(coalesce(p.productDisplayNameVi, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.brandName, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.variantName, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.variantNameVi, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.baseColour, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.baseColourVi, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.colour1, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.colour1Vi, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.colour2, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.colour2Vi, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.gender, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.genderVi, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.material, '')) like concat('%', :keyword, '%')
               or lower(coalesce(p.materialVi, '')) like concat('%', :keyword, '%')
            order by p.id asc
            """)
    List<Product> findMockAiCandidatesByKeyword(@Param("keyword") String keyword, Pageable pageable);

    @Query(
            value = """
                    select p
                    from Product p
                    where p.updatedAt > :updatedAfter
                       or exists (
                            select v.id
                            from ProductVariant v
                            where v.product = p
                              and v.updatedAt > :updatedAfter
                       )
                       or exists (
                            select price.id
                            from ProductPrice price
                            where price.product = p
                              and price.updatedAt > :updatedAfter
                       )
                       or exists (
                            select attr.id
                            from ProductAttribute attr
                            where attr.product = p
                              and attr.updatedAt > :updatedAfter
                       )
                    """,
            countQuery = """
                    select count(p)
                    from Product p
                    where p.updatedAt > :updatedAfter
                       or exists (
                            select v.id
                            from ProductVariant v
                            where v.product = p
                              and v.updatedAt > :updatedAfter
                       )
                       or exists (
                            select price.id
                            from ProductPrice price
                            where price.product = p
                              and price.updatedAt > :updatedAfter
                       )
                       or exists (
                            select attr.id
                            from ProductAttribute attr
                            where attr.product = p
                              and attr.updatedAt > :updatedAfter
                       )
                    """
    )
    Page<Product> findProductsUpdatedAfter(@Param("updatedAfter") Instant updatedAfter, Pageable pageable);
}
