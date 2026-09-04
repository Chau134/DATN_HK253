package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.Blog;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface BlogRepository extends JpaRepository<Blog, Long> {
    
    @EntityGraph(attributePaths = "author")
    List<Blog> findAllByOrderByCreatedAtDescIdDesc();
    
    @Query("""
            select b from Blog b
            left join fetch b.author a
            where b.status = 'PUBLISHED'
              and (b.publishedAt is null or b.publishedAt <= :now)
            order by coalesce(b.publishedAt, b.createdAt) desc, b.id desc
            """)
    List<Blog> findPublishedBlogs(@Param("now") Instant now);
    
    Optional<Blog> findBySlug(String slug);
}
