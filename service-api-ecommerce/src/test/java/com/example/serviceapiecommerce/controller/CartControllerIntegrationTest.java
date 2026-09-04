package com.example.serviceapiecommerce.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest(properties = {
        "app.security.jwt.secret=test-secret-for-cart-controller-integration-test-1234567890",
        "app.security.jwt.access-token-ttl-seconds=900",
        "app.security.jwt.refresh-token-ttl-days=30",
        "ai.service.enabled=false"
})
@AutoConfigureMockMvc
class CartControllerIntegrationTest {
    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private ProductVariantRepository productVariantRepository;

    @Autowired
    private ProductPriceRepository productPriceRepository;

    @Autowired
    private ProductImageRepository productImageRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void cartEndpointsRequireAuthentication() throws Exception {
        mockMvc.perform(get("/api/cart"))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(post("/api/cart/items")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_variant_id", 1,
                                "quantity", 1
                        ))))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void addUpdateDeleteAndGetCartItems() throws Exception {
        ProductVariant variant = seedVariant(
                "Cart Phase10 Shoe " + UUID.randomUUID(),
                true,
                true,
                10,
                new BigDecimal("100000.00"),
                new BigDecimal("80000.00")
        );
        String accessToken = registerCustomerAccessToken();

        mockMvc.perform(get("/api/cart")
                        .header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ACTIVE"))
                .andExpect(jsonPath("$.item_count").value(0))
                .andExpect(jsonPath("$.total_quantity").value(0))
                .andExpect(jsonPath("$.subtotal").value(0))
                .andExpect(jsonPath("$.items.length()").value(0));

        mockMvc.perform(post("/api/cart/items")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_variant_id", variant.getId(),
                                "quantity", 2
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(1))
                .andExpect(jsonPath("$.total_quantity").value(2))
                .andExpect(jsonPath("$.subtotal").value(200000.00))
                .andExpect(jsonPath("$.items[0].product_variant_id").value(variant.getId().intValue()))
                .andExpect(jsonPath("$.items[0].quantity").value(2))
                .andExpect(jsonPath("$.items[0].effective_price").value(100000.00))
                .andExpect(jsonPath("$.items[0].line_subtotal").value(200000.00))
                .andExpect(jsonPath("$.items[0].available").value(true));

        MvcResult duplicateAdd = mockMvc.perform(post("/api/cart/items")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_variant_id", variant.getId(),
                                "quantity", 1
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(1))
                .andExpect(jsonPath("$.total_quantity").value(3))
                .andExpect(jsonPath("$.subtotal").value(300000.00))
                .andExpect(jsonPath("$.items.length()").value(1))
                .andExpect(jsonPath("$.items[0].quantity").value(3))
                .andReturn();

        JsonNode cart = objectMapper.readTree(duplicateAdd.getResponse().getContentAsString());
        long cartItemId = cart.get("items").get(0).get("id").asLong();

        mockMvc.perform(patch("/api/cart/items/{cartItemId}", cartItemId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of("quantity", 4))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(1))
                .andExpect(jsonPath("$.total_quantity").value(4))
                .andExpect(jsonPath("$.subtotal").value(400000.00))
                .andExpect(jsonPath("$.items[0].quantity").value(4));

        mockMvc.perform(delete("/api/cart/items/{cartItemId}", cartItemId)
                        .header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(0))
                .andExpect(jsonPath("$.total_quantity").value(0))
                .andExpect(jsonPath("$.subtotal").value(0))
                .andExpect(jsonPath("$.items.length()").value(0));

        mockMvc.perform(get("/api/cart")
                        .header("Authorization", "Bearer " + accessToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(0))
                .andExpect(jsonPath("$.items.length()").value(0));
    }

    @Test
    void addRejectsInactiveUnavailableOutOfStockAndInsufficientStockVariants() throws Exception {
        String accessToken = registerCustomerAccessToken();
        ProductVariant inactive = seedVariant(
                "Cart Phase10 Inactive " + UUID.randomUUID(),
                false,
                true,
                5,
                new BigDecimal("90000.00"),
                null
        );
        ProductVariant unavailable = seedVariant(
                "Cart Phase10 Unavailable " + UUID.randomUUID(),
                true,
                false,
                5,
                new BigDecimal("90000.00"),
                null
        );
        ProductVariant outOfStock = seedVariant(
                "Cart Phase10 Out Stock " + UUID.randomUUID(),
                true,
                true,
                0,
                new BigDecimal("90000.00"),
                null
        );
        ProductVariant lowStock = seedVariant(
                "Cart Phase10 Low Stock " + UUID.randomUUID(),
                true,
                true,
                2,
                new BigDecimal("90000.00"),
                null
        );

        expectAddConflict(accessToken, inactive.getId(), 1);
        expectAddConflict(accessToken, unavailable.getId(), 1);
        expectAddConflict(accessToken, outOfStock.getId(), 1);
        expectAddConflict(accessToken, lowStock.getId(), 3);
    }

    private void expectAddConflict(String accessToken, Long productVariantId, int quantity) throws Exception {
        mockMvc.perform(post("/api/cart/items")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_variant_id", productVariantId,
                                "quantity", quantity
                        ))))
                .andExpect(status().isConflict());
    }

    private String registerCustomerAccessToken() throws Exception {
        String email = "cart-" + UUID.randomUUID() + "@example.test";
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "email", email,
                                "password", "Password123!",
                                "full_name", "Cart Test User"
                        ))))
                .andExpect(status().isCreated())
                .andReturn();
        JsonNode response = objectMapper.readTree(result.getResponse().getContentAsString());
        return response.get("access_token").asText();
    }

    private ProductVariant seedVariant(
            String title,
            boolean active,
            boolean available,
            int stock,
            BigDecimal price,
            BigDecimal discountedPrice
    ) {
        Instant now = Instant.now();
        Product product = new Product();
        product.setId(ThreadLocalRandom.current().nextLong(100_000_000L, 900_000_000L));
        product.setExternalId(product.getId() + 1_000_000);
        product.setArticleNumber("CART-" + product.getId());
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setBrandName("Phase10 Cart Brand");
        product.setGender("Unisex");
        product.setBaseColour("Black");
        product.setMainImage("https://cdn.test/cart/" + product.getId() + "-main.jpg");
        product.setCatalogAddDate(now);
        product.setCreatedAt(now);
        product.setUpdatedAt(now);
        productRepository.save(product);

        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        variant.setSkuId(product.getId() + 20_000);
        variant.setOptionName("Size");
        variant.setOptionValue("M");
        variant.setUnifiedSize("M");
        variant.setInventoryCount(stock);
        variant.setAvailable(available);
        variant.setActive(active);
        variant.setCreatedAt(now);
        variant.setUpdatedAt(now);
        productVariantRepository.save(variant);

        ProductPrice productPrice = new ProductPrice();
        productPrice.setProduct(product);
        productPrice.setSellingPrice(price);
        productPrice.setImportPrice(discountedPrice);
        productPrice.setVat(new BigDecimal("0.00"));
        productPrice.setCreatedAt(now);
        productPrice.setUpdatedAt(now);
        productPriceRepository.save(productPrice);

        ProductImage image = new ProductImage();
        image.setProduct(product);
        image.setImageType("MAIN");
        image.setImageUrl("https://cdn.test/cart/" + product.getId() + ".jpg");
        image.setSortOrder(0);
        image.setCreatedAt(now);
        productImageRepository.save(image);
        return variant;
    }
}
