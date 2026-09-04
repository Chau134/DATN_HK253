package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductAttribute;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.ProductAttributeRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ProductCardResolverImplTest {
    @Mock
    private ProductRepository productRepository;

    @Mock
    private ProductImageRepository productImageRepository;

    @Mock
    private ProductPriceRepository productPriceRepository;

    @Mock
    private ProductVariantRepository productVariantRepository;

    @Mock
    private ProductAttributeRepository productAttributeRepository;

    @Test
    void resolveHydratesProductCardsInAiRankingOrder() {
        ProductCardResolverImpl resolver = resolver();
        Product first = product(1L, "First");
        Product second = product(2L, "Second");
        ProductPrice firstPrice = price(first, "100000.00", null);
        ProductPrice secondPrice = price(second, "150000.00", "120000.00");
        ProductImage firstImage = image(first, "https://cdn.test/first.jpg");
        ProductVariant firstVariant = variant(first, 3, true, true);
        ProductVariant secondVariant = variant(second, 5, true, true);
        ProductVariant unavailableSecondVariant = variant(second, 100, false, true);
        List<Long> productIds = List.of(2L, 1L);

        when(productRepository.findAllByIdInForAiIndexing(productIds)).thenReturn(List.of(first, second));
        when(productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds))
                .thenReturn(List.of(firstImage));
        when(productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds))
                .thenReturn(List.of(firstPrice, secondPrice));
        when(productVariantRepository.findByProductIdIn(productIds))
                .thenReturn(List.of(firstVariant, secondVariant, unavailableSecondVariant));
        when(productAttributeRepository.findByProductIdIn(productIds)).thenReturn(List.of());

        var cards = resolver.resolve(List.of(
                new AiProductResultDto("2", 0.95, "hybrid"),
                new AiProductResultDto("1", 0.90, "hybrid")
        ));

        assertThat(cards).extracting("productId").containsExactly("2", "1");
        assertThat(cards.get(0).title()).isEqualTo("Second");
        assertThat(cards.get(0).effectivePrice()).isEqualByComparingTo("150000.00");
        assertThat(cards.get(0).totalStock()).isEqualTo(5);
        assertThat(cards.get(0).available()).isTrue();
        assertThat(cards.get(0).imageUrl()).isEqualTo("https://cdn.test/2-main.jpg");
        assertThat(cards.get(0).aiScore()).isEqualTo(0.95);
        assertThat(cards.get(1).imageUrl()).isEqualTo("https://cdn.test/first.jpg");
    }

    @Test
    void resolveSkipsInvalidDuplicateAndMissingProductIds() {
        ProductCardResolverImpl resolver = resolver();
        Product product = product(1L, "First");
        List<Long> productIds = List.of(1L, 404L);

        when(productRepository.findAllByIdInForAiIndexing(productIds)).thenReturn(List.of(product));
        when(productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds)).thenReturn(List.of());
        when(productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds)).thenReturn(List.of());
        when(productVariantRepository.findByProductIdIn(productIds)).thenReturn(List.of(variant(product, 1, true, true)));
        when(productAttributeRepository.findByProductIdIn(productIds)).thenReturn(List.of());

        var cards = resolver.resolve(List.of(
                new AiProductResultDto("bad", 1.0, "text"),
                new AiProductResultDto("1", 0.9, "text"),
                new AiProductResultDto("1", 0.8, "text"),
                new AiProductResultDto("404", 0.7, "text")
        ));

        assertThat(cards).extracting("productId").containsExactly("1");
        assertThat(cards.getFirst().aiScore()).isEqualTo(0.9);
    }

    @Test
    void resolveIncludesUnavailableProductsAndFiltersInactiveProducts() {
        ProductCardResolverImpl resolver = resolver();
        Product available = product(1L, "Available");
        Product unavailable = product(2L, "Unavailable");
        Product inactive = product(3L, "Inactive");
        Product activeButNotAvailable = product(4L, "Active but not available");
        Product explicitlyActiveWithoutVariants = product(5L, "Explicitly active without variants");
        List<Long> productIds = List.of(1L, 2L, 3L, 4L, 5L);

        when(productRepository.findAllByIdInForAiIndexing(productIds))
                .thenReturn(List.of(
                        available,
                        unavailable,
                        inactive,
                        activeButNotAvailable,
                        explicitlyActiveWithoutVariants
                ));
        when(productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds)).thenReturn(List.of());
        when(productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds)).thenReturn(List.of());
        when(productVariantRepository.findByProductIdIn(productIds)).thenReturn(List.of(
                variant(available, 3, true, true),
                variant(unavailable, 4, false, true),
                variant(inactive, 5, true, true),
                variant(activeButNotAvailable, 6, true, false)
        ));
        when(productAttributeRepository.findByProductIdIn(productIds)).thenReturn(List.of(
                attribute(inactive, "flag:active", "false"),
                attribute(explicitlyActiveWithoutVariants, "flag:active", "true")
        ));

        var cards = resolver.resolve(List.of(
                new AiProductResultDto("1", 0.99, "text"),
                new AiProductResultDto("2", 0.98, "text"),
                new AiProductResultDto("3", 0.97, "text"),
                new AiProductResultDto("4", 0.96, "text"),
                new AiProductResultDto("5", 0.95, "text")
        ));

        assertThat(cards).extracting("productId").containsExactly("1", "2", "5");
        assertThat(cards.get(1).available()).isFalse();
        assertThat(cards.get(1).totalStock()).isZero();
        assertThat(cards.get(2).available()).isFalse();
        assertThat(cards.get(2).totalStock()).isZero();
    }

    private ProductCardResolverImpl resolver() {
        return new ProductCardResolverImpl(
                productRepository,
                productImageRepository,
                productPriceRepository,
                productVariantRepository,
                productAttributeRepository
        );
    }

    private static Product product(Long id, String title) {
        Product product = new Product();
        product.setId(id);
        product.setExternalId(id + 1000);
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setBrandName("Codex");
        product.setMainImage("https://cdn.test/" + id + "-main.jpg");
        return product;
    }

    private static ProductImage image(Product product, String imageUrl) {
        ProductImage image = new ProductImage();
        image.setProduct(product);
        image.setImageUrl(imageUrl);
        return image;
    }

    private static ProductPrice price(Product product, String price, String discountedPrice) {
        ProductPrice productPrice = new ProductPrice();
        productPrice.setProduct(product);
        productPrice.setSellingPrice(new BigDecimal(price));
        productPrice.setImportPrice(discountedPrice == null ? null : new BigDecimal(discountedPrice));
        return productPrice;
    }

    private static ProductVariant variant(Product product, int stock, boolean available, boolean active) {
        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        variant.setInventoryCount(stock);
        variant.setAvailable(available);
        variant.setActive(active);
        return variant;
    }

    private static ProductAttribute attribute(Product product, String key, String value) {
        ProductAttribute attribute = new ProductAttribute();
        attribute.setProduct(product);
        attribute.setAttrKey(key);
        attribute.setAttrValue(value);
        return attribute;
    }
}
