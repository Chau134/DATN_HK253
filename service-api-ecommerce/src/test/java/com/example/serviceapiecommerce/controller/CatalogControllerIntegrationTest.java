package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.entity.Category;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductCategory;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductReviewSummary;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.CategoryRepository;
import com.example.serviceapiecommerce.repository.ProductCategoryRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductReviewSummaryRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.transaction.annotation.Transactional;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class CatalogControllerIntegrationTest {
    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private CategoryRepository categoryRepository;

    @Autowired
    private ProductCategoryRepository productCategoryRepository;

    @Autowired
    private ProductImageRepository productImageRepository;

    @Autowired
    private ProductVariantRepository productVariantRepository;

    @Autowired
    private ProductPriceRepository productPriceRepository;

    @Autowired
    private ProductReviewSummaryRepository productReviewSummaryRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private long nextProductId = ThreadLocalRandom.current().nextLong(100_000_000L, 900_000_000L);

    @Test
    void productsEndpointSupportsBasicFiltersAndStablePageResponse() throws Exception {
        String token = "phase9-" + UUID.randomUUID();
        Category category = category(token + "-category", true);
        SeedProduct matched = seedProduct(
                token + " Runner",
                "Phase9 Brand",
                "Men",
                category,
                true,
                new BigDecimal("150000.00"),
                new BigDecimal("120000.00")
        );
        seedProduct(
                token + " Runner Hidden",
                "Phase9 Brand",
                "Men",
                category,
                false,
                new BigDecimal("180000.00"),
                null
        );
        productReviewSummaryRepository.flush();

        mockMvc.perform(get("/api/products")
                        .param("keyword", token)
                        .param("category_id", String.valueOf(category.getId()))
                        .param("brand", "Phase9 Brand")
                        .param("gender", "Men")
                        .param("available", "true")
                        .param("min_price", "100000")
                        .param("max_price", "200000")
                        .param("sort", "name_asc")
                        .param("page", "0")
                        .param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.page").value(0))
                .andExpect(jsonPath("$.size").value(10))
                .andExpect(jsonPath("$.total_elements").value(1))
                .andExpect(jsonPath("$.items.length()").value(1))
                .andExpect(jsonPath("$.items[0].id").value(matched.product().getId().intValue()))
                .andExpect(jsonPath("$.items[0].title").value(token + " Runner"))
                .andExpect(jsonPath("$.items[0].price.effective_price").value(150000.00))
                .andExpect(jsonPath("$.items[0].available").value(true))
                .andExpect(jsonPath("$.items[0].total_stock").value(7))
                .andExpect(jsonPath("$.items[0].categories[0].id").value(category.getId().intValue()))
                .andExpect(jsonPath("$.items[0].review_summary.average_rating").value(4.5));
    }

    @Test
    void productDetailIncludesImagesVariantsCategoriesPriceAndReviewSummary() throws Exception {
        String token = "phase9-detail-" + UUID.randomUUID();
        Category category = category(token + "-category", true);
        SeedProduct seed = seedProduct(
                token + " Jacket",
                "Phase9 Detail Brand",
                "Women",
                category,
                true,
                new BigDecimal("250000.00"),
                null
        );
        productReviewSummaryRepository.flush();

        mockMvc.perform(get("/api/products/{productId}", seed.product().getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(seed.product().getId().intValue()))
                .andExpect(jsonPath("$.title").value(token + " Jacket"))
                .andExpect(jsonPath("$.brand").value("Phase9 Detail Brand"))
                .andExpect(jsonPath("$.price.price").value(250000.00))
                .andExpect(jsonPath("$.image_url").value("https://cdn.test/" + seed.product().getId() + "-main.jpg"))
                .andExpect(jsonPath("$.images[0].image_url").value("https://cdn.test/" + seed.product().getId() + "-main.jpg"))
                .andExpect(jsonPath("$.images[1].image_url").value("https://cdn.test/" + seed.product().getId() + ".jpg"))
                .andExpect(jsonPath("$.variants[0].option_name").value("Size"))
                .andExpect(jsonPath("$.variants[0].inventory_count").value(7))
                .andExpect(jsonPath("$.categories[0].name").value(category.getCategoryName()))
                .andExpect(jsonPath("$.review_summary.review_count").value(3));
    }

    @Test
    void categoriesEndpointReturnsOnlyActiveCategories() throws Exception {
        String token = "phase9-category-" + UUID.randomUUID();
        Category active = category(token + "-active", true);
        Category inactive = category(token + "-inactive", false);
        categoryRepository.flush();

        MvcResult result = mockMvc.perform(get("/api/categories"))
                .andExpect(status().isOk())
                .andReturn();

        JsonNode response = objectMapper.readTree(result.getResponse().getContentAsString());
        List<String> names = new ArrayList<>();
        response.forEach(node -> names.add(node.get("name").asText()));

        assertThat(names).contains(active.getCategoryName());
        assertThat(names).doesNotContain(inactive.getCategoryName());
    }

    private SeedProduct seedProduct(
            String title,
            String brand,
            String gender,
            Category category,
            boolean available,
            BigDecimal price,
            BigDecimal discountedPrice
    ) {
        Product product = product(title, brand, gender);
        productRepository.save(product);

        ProductCategory productCategory = new ProductCategory();
        productCategory.setProduct(product);
        productCategory.setCategory(category);
        productCategoryRepository.save(productCategory);

        ProductImage image = new ProductImage();
        image.setProduct(product);
        image.setImageType("MAIN");
        image.setImageUrl("https://cdn.test/" + product.getId() + ".jpg");
        image.setSortOrder(0);
        image.setCreatedAt(Instant.now());
        productImageRepository.save(image);

        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        variant.setSkuId(product.getId() + 10_000);
        variant.setOptionName("Size");
        variant.setOptionValue("M");
        variant.setUnifiedSize("M");
        variant.setInventoryCount(available ? 7 : 0);
        variant.setAvailable(available);
        variant.setActive(true);
        variant.setCreatedAt(Instant.now());
        variant.setUpdatedAt(Instant.now());
        productVariantRepository.save(variant);

        ProductPrice productPrice = new ProductPrice();
        productPrice.setProduct(product);
        productPrice.setSellingPrice(price);
        productPrice.setImportPrice(discountedPrice);
        productPrice.setVat(new BigDecimal("0.00"));
        productPrice.setCreatedAt(Instant.now());
        productPrice.setUpdatedAt(Instant.now());
        productPriceRepository.save(productPrice);

        ProductReviewSummary summary = new ProductReviewSummary();
        summary.setProduct(product);
        summary.setReviewCount(3);
        summary.setApprovedReviewCount(3);
        summary.setAverageRating(new BigDecimal("4.50"));
        summary.setRating1Count(0);
        summary.setRating2Count(0);
        summary.setRating3Count(0);
        summary.setRating4Count(1);
        summary.setRating5Count(2);
        summary.setUpdatedAt(Instant.now());
        productReviewSummaryRepository.save(summary);

        return new SeedProduct(product);
    }

    private Product product(String title, String brand, String gender) {
        Product product = new Product();
        product.setId(++nextProductId);
        product.setExternalId(product.getId() + 1_000_000);
        product.setArticleNumber("ART-" + product.getId());
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setVariantName("Regular");
        product.setVariantNameVi("Thuong");
        product.setBrandName(brand);
        product.setGender(gender);
        product.setGenderVi(gender);
        product.setBaseColour("Black");
        product.setBaseColourVi("Den");
        product.setSeason("Summer");
        product.setSeasonVi("He");
        product.setYear(2026);
        product.setProductUsage("Casual");
        product.setProductUsageVi("Hang ngay");
        product.setMaterial("Cotton");
        product.setMaterialVi("Cotton");
        product.setFit("Regular");
        product.setFitVi("Vua van");
        product.setMainImage("https://cdn.test/" + product.getId() + "-main.jpg");
        product.setDescription(title + " description");
        product.setDescriptionVi(title + " mo ta");
        product.setCatalogAddDate(Instant.now());
        product.setCreatedAt(Instant.now());
        product.setUpdatedAt(Instant.now());
        return product;
    }

    private Category category(String name, boolean active) {
        Category category = new Category();
        category.setSourceCategoryId(ThreadLocalRandom.current().nextLong(1_000_000L, 9_000_000L));
        category.setCategoryLevel("type");
        category.setCategoryName(name);
        category.setCategoryNameVi(name + " vi");
        category.setIsActive(active);
        return categoryRepository.save(category);
    }

    private record SeedProduct(Product product) {
    }
}
