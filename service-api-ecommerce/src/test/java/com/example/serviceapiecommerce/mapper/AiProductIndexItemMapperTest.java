package com.example.serviceapiecommerce.mapper;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.example.serviceapiecommerce.dto.ai.AiProductIndexItemDto;
import com.example.serviceapiecommerce.entity.Category;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductCategory;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class AiProductIndexItemMapperTest {
    private final AiProductIndexItemMapper mapper = new AiProductIndexItemMapper();

    @Test
    void mapsProductAggregateToAiIndexItem() {
        Product product = product();
        ProductPrice price = price();

        ProductVariant sellableVariant = variant("M", "EU-M", 3, true, true, "2026-05-14T02:00:00Z");
        ProductVariant inactiveVariant = variant("S", "EU-S", 9, true, false, "2026-05-14T03:00:00Z");

        ProductAttribute searchCategoryAttribute = attribute(
                "search_category",
                "hoodie, topwear",
                null,
                "2026-05-14T01:30:00Z"
        );
        ProductAttribute searchKeywordsViAttribute = attribute(
                "search_keywords_vi",
                null,
                "ao hoodie, ao ni",
                "2026-05-14T04:00:00Z"
        );

        AiProductIndexItemDto dto = mapper.toDto(
                product,
                List.of(image(2L, 20, "https://cdn.test/second.jpg"), image(1L, 10, "https://cdn.test/first.jpg")),
                List.of(productCategory()),
                List.of(inactiveVariant, sellableVariant),
                price,
                List.of(searchCategoryAttribute, searchKeywordsViAttribute)
        );

        assertEquals("42", dto.productId());
        assertEquals("Black Hoodie", dto.productDisplayName());
        assertEquals("Ao hoodie den", dto.productDisplayNameVi());
        assertEquals("Soft cotton hoodie", dto.description());
        assertEquals("Ao hoodie cotton mem", dto.descriptionVi());
        assertEquals("Codex Wear", dto.brandName());
        assertEquals("Black", dto.baseColour());
        assertEquals("Den", dto.baseColourVi());
        assertEquals("Cotton", dto.material());
        assertEquals("Regular", dto.fit());
        assertEquals("Winter", dto.season());
        assertEquals("Casual", dto.productUsage());
        assertEquals("Women", dto.gender());
        assertEquals("hoodie_sweatshirt", dto.categories().getFirst().categoryCode());
        assertEquals("article_type", dto.categories().getFirst().categoryLevel());
        assertEquals("Hoodies", dto.categories().getFirst().categoryName());
        assertEquals(List.of("S", "M"), dto.optionValue());
        assertEquals(List.of("EU-S", "EU-M"), dto.unifiedSize());
        assertEquals(3, dto.inventoryCount());
        assertTrue(dto.available());
        assertTrue(dto.active());
        assertEquals(new BigDecimal("399000.00"), dto.sellingPrice());
        assertEquals(new BigDecimal("10.00"), dto.vat());
        assertEquals(List.of("https://cdn.test/first.jpg", "https://cdn.test/second.jpg"), dto.imageUrls());
        assertEquals("hoodie, topwear", dto.attributes().get("search_category"));
        assertEquals("ao hoodie, ao ni", dto.attributesVi().get("search_keywords_vi"));
        assertEquals(Instant.parse("2026-05-14T00:00:00Z"), dto.updatedAt());
    }

    @Test
    void productWithoutVariantsOrActiveOverrideIsInactiveAndUnavailable() {
        AiProductIndexItemDto dto = mapper.toDto(
                product(),
                List.of(),
                List.of(),
                List.of(),
                null,
                List.of()
        );

        assertEquals(List.of("https://cdn.test/main.jpg"), dto.imageUrls());
        assertEquals(0, dto.inventoryCount());
        assertFalse(dto.available());
        assertFalse(dto.active());
    }

    @Test
    void excludesVideoMediaFromImageIndexingContract() {
        AiProductIndexItemDto dto = mapper.toDto(
                product(),
                List.of(
                        image(1L, 10, "https://cdn.test/first.jpg?width=1200"),
                        image(2L, 20, "https://cdn.test/video/master.m3u8?ts=1776175167632"),
                        image(3L, 30, "https://cdn.test/preview.MP4?download=1"),
                        image(4L, 40, "https://cdn.test/second.webp")
                ),
                List.of(),
                List.of(),
                null,
                List.of()
        );

        assertEquals(
                List.of("https://cdn.test/first.jpg?width=1200", "https://cdn.test/second.webp"),
                dto.imageUrls()
        );
    }

    @Test
    void doesNotUseVideoMainMediaAsImageFallback() {
        Product product = product();
        product.setMainImage("https://cdn.test/video/master.m3u8?ts=1776175167632");

        AiProductIndexItemDto dto = mapper.toDto(
                product,
                List.of(),
                List.of(),
                List.of(),
                null,
                List.of()
        );

        assertEquals(List.of(), dto.imageUrls());
    }

    @Test
    void explicitProductActiveFlagAllowsVariantlessProductButKeepsItUnavailable() {
        AiProductIndexItemDto dto = mapper.toDto(
                product(),
                List.of(),
                List.of(),
                List.of(),
                null,
                List.of(attribute("flag:active", "true", null, "2026-05-14T05:00:00Z"))
        );

        assertTrue(dto.active());
        assertFalse(dto.available());
        assertEquals(0, dto.inventoryCount());
    }

    @Test
    void zeroStockVariantIsActiveButNotSellable() {
        AiProductIndexItemDto dto = mapper.toDto(
                product(),
                List.of(),
                List.of(),
                List.of(variant("M", "EU-M", 0, true, true, "2026-05-14T02:00:00Z")),
                null,
                List.of()
        );

        assertTrue(dto.active());
        assertFalse(dto.available());
        assertEquals(0, dto.inventoryCount());
    }

    @Test
    void explicitInactiveFlagOverridesSellableVariants() {
        AiProductIndexItemDto dto = mapper.toDto(
                product(),
                List.of(),
                List.of(),
                List.of(variant("M", "EU-M", 3, true, true, "2026-05-14T02:00:00Z")),
                null,
                List.of(attribute("flag:active", "false", null, "2026-05-14T05:00:00Z"))
        );

        assertFalse(dto.active());
        assertFalse(dto.available());
        assertEquals(0, dto.inventoryCount());
    }

    @Test
    void latestValidProductActiveOverrideWins() {
        AiProductIndexItemDto dto = mapper.toDto(
                product(),
                List.of(),
                List.of(),
                List.of(variant("M", "EU-M", 3, true, true, "2026-05-14T02:00:00Z")),
                null,
                List.of(
                        attribute("flag:active", "true", null, "2026-05-14T04:00:00Z"),
                        attribute("flag:active", "false", null, "2026-05-14T05:00:00Z")
                )
        );

        assertFalse(dto.active());
        assertFalse(dto.available());
        assertEquals(0, dto.inventoryCount());
    }

    private static Product product() {
        Product product = new Product();
        product.setId(42L);
        product.setExternalId(10042L);
        product.setProductDisplayName("Black Hoodie");
        product.setProductDisplayNameVi("Ao hoodie den");
        product.setVariantName("Oversized");
        product.setVariantNameVi("Form rong");
        product.setDescription("Soft cotton hoodie");
        product.setDescriptionVi("Ao hoodie cotton mem");
        product.setBrandName("Codex Wear");
        product.setBaseColour("Black");
        product.setColour1("White");
        product.setColour2("Black");
        product.setBaseColourVi("Den");
        product.setColour1Vi("Trang");
        product.setMaterial("Cotton");
        product.setMaterialVi("Cotton");
        product.setFit("Regular");
        product.setFitVi("Vua van");
        product.setSeason("Winter");
        product.setSeasonVi("Mua dong");
        product.setProductUsage("Casual");
        product.setProductUsageVi("Hang ngay");
        product.setGender("Women");
        product.setGenderVi("Nu");
        product.setMainImage("https://cdn.test/main.jpg");
        product.setUpdatedAt(Instant.parse("2026-05-14T00:00:00Z"));
        return product;
    }

    private static ProductImage image(Long id, Integer sortOrder, String imageUrl) {
        ProductImage image = new ProductImage();
        image.setId(id);
        image.setSortOrder(sortOrder);
        image.setImageUrl(imageUrl);
        return image;
    }

    private static ProductCategory productCategory() {
        Category category = new Category();
        category.setId(5L);
        category.setSourceCategoryId(50L);
        category.setCategoryLevel("article_type");
        category.setCategoryName("Hoodies");
        category.setCategoryNameVi("Ao hoodie");
        category.setCanonicalCode("hoodie_sweatshirt");
        category.setIsActive(true);

        ProductCategory productCategory = new ProductCategory();
        productCategory.setCategory(category);
        return productCategory;
    }

    private static ProductVariant variant(
            String optionValue,
            String unifiedSize,
            Integer inventoryCount,
            Boolean available,
            Boolean active,
            String updatedAt
    ) {
        ProductVariant variant = new ProductVariant();
        variant.setOptionValue(optionValue);
        variant.setUnifiedSize(unifiedSize);
        variant.setInventoryCount(inventoryCount);
        variant.setAvailable(available);
        variant.setActive(active);
        variant.setUpdatedAt(Instant.parse(updatedAt));
        return variant;
    }

    private static ProductPrice price() {
        ProductPrice price = new ProductPrice();
        price.setSellingPrice(new BigDecimal("399000.00"));
        price.setImportPrice(new BigDecimal("299000.00"));
        price.setVat(new BigDecimal("10.00"));
        price.setUpdatedAt(Instant.parse("2026-05-14T01:00:00Z"));
        return price;
    }

    private static ProductAttribute attribute(String key, String value, String valueVi, String updatedAt) {
        ProductAttribute attribute = new ProductAttribute();
        attribute.setAttrKey(key);
        attribute.setAttrValue(value);
        attribute.setAttrValueVi(valueVi);
        attribute.setUpdatedAt(Instant.parse(updatedAt));
        return attribute;
    }
}
