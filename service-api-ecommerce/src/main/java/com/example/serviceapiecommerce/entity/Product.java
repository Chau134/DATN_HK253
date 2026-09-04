package com.example.serviceapiecommerce.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.ColumnDefault;

import java.time.Instant;

@Getter
@Setter
@Entity
@Table(name = "products")
public class Product {
    @Id
    @Column(name = "id", nullable = false)
    private Long id;

    @Column(name = "external_id")
    private Long externalId;

    @Column(name = "article_number", length = 100)
    private String articleNumber;

    @Column(name = "product_display_name", nullable = false)
    private String productDisplayName;

    @Column(name = "variant_name")
    private String variantName;

    @Column(name = "brand_name", length = 150)
    private String brandName;

    @Column(name = "age_group", length = 100)
    private String ageGroup;

    @Column(name = "gender", length = 50)
    private String gender;

    @Column(name = "base_colour", length = 100)
    private String baseColour;

    @Column(name = "colour1", length = 100)
    private String colour1;

    @Column(name = "colour2", length = 100)
    private String colour2;

    @Column(name = "season", length = 50)
    private String season;

    @Column(name = "year")
    private Integer year;

    @Column(name = "product_usage", length = 100)
    private String productUsage;

    @Column(name = "material", length = 150)
    private String material;

    @Column(name = "fit", length = 150)
    private String fit;

    @Lob
    @Column(name = "main_image", columnDefinition = "longtext")
    private String mainImage;

    @Lob
    @Column(name = "description", columnDefinition = "longtext")
    private String description;

    @Column(name = "catalog_add_date")
    private Instant catalogAddDate;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "created_at")
    private Instant createdAt;

    @ColumnDefault("CURRENT_TIMESTAMP(6)")
    @Column(name = "updated_at")
    private Instant updatedAt;

    @Column(name = "product_display_name_vi")
    private String productDisplayNameVi;

    @Column(name = "variant_name_vi")
    private String variantNameVi;

    @Column(name = "age_group_vi", length = 100)
    private String ageGroupVi;

    @Column(name = "gender_vi", length = 50)
    private String genderVi;

    @Column(name = "base_colour_vi", length = 100)
    private String baseColourVi;

    @Column(name = "colour1_vi", length = 100)
    private String colour1Vi;

    @Column(name = "colour2_vi", length = 100)
    private String colour2Vi;

    @Column(name = "season_vi", length = 50)
    private String seasonVi;

    @Column(name = "product_usage_vi", length = 100)
    private String productUsageVi;

    @Column(name = "material_vi", length = 150)
    private String materialVi;

    @Column(name = "fit_vi", length = 150)
    private String fitVi;

    @Lob
    @Column(name = "description_vi", columnDefinition = "longtext")
    private String descriptionVi;


}
