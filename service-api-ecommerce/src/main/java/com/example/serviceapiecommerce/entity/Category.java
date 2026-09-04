package com.example.serviceapiecommerce.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;

@Getter
@Setter
@Entity
@Table(name = "categories")
public class Category {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;

    @Column(name = "source_category_id")
    private Long sourceCategoryId;

    @Column(name = "category_level", nullable = false, length = 50)
    private String categoryLevel;

    @Column(name = "category_name", nullable = false, length = 150)
    private String categoryName;

    @ColumnDefault("1")
    @Column(name = "is_active")
    private Boolean isActive;

    @Column(name = "category_name_vi", length = 150)
    private String categoryNameVi;

    @Column(name = "parent_id")
    private Long parentId;

    @Column(name = "canonical_code", length = 100, unique = true)
    private String canonicalCode;
}