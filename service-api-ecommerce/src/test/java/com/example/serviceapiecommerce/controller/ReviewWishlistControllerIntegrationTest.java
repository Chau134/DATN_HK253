package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductReviewSummary;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserRole;
import com.example.serviceapiecommerce.repository.CustomerAddressRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductReviewSummaryRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.repository.UserRoleRepository;
import com.example.serviceapiecommerce.repository.WishlistItemRepository;
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
        "app.security.jwt.secret=test-secret-for-review-wishlist-controller-integration-test-1234567890",
        "app.security.jwt.access-token-ttl-seconds=900",
        "app.security.jwt.refresh-token-ttl-days=30",
        "ai.service.enabled=false"
})
@AutoConfigureMockMvc
class ReviewWishlistControllerIntegrationTest {
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

    @Autowired
    private ProductReviewSummaryRepository productReviewSummaryRepository;

    @Autowired
    private WishlistItemRepository wishlistItemRepository;

    @Autowired
    private CustomerAddressRepository customerAddressRepository;

    @Autowired
    private UserAccountRepository userAccountRepository;

    @Autowired
    private UserRoleRepository userRoleRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void customerReviewRequiresPaidPurchaseBlocksDuplicateAndAdminApprovalUpdatesSummary() throws Exception {
        ProductVariant variant = seedVariant("Phase15 Review Shoe " + UUID.randomUUID(), 3);
        AuthSession user = registerCustomer();
        AuthSession admin = registerAdmin();
        CustomerAddress address = seedAddress(user.userId());

        long cartId = addToCart(user.accessToken(), variant.getId(), 1);
        JsonNode order = checkout(user.accessToken(), cartId, address.getId());
        long orderId = order.get("id").asLong();
        long orderItemId = order.get("items").get(0).get("id").asLong();
        long paymentId = createCodPayment(user.accessToken(), orderId, "phase15-review-payment-" + UUID.randomUUID())
                .get("id")
                .asLong();
        confirmCodPayment(admin.accessToken(), paymentId, "phase15-review-confirm-" + UUID.randomUUID());

        MvcResult createdResult = mockMvc.perform(post("/api/reviews")
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "order_item_id", orderItemId,
                                "rating", 5,
                                "title", "Great fit",
                                "content", "The snapshot product is exactly what I bought."
                        ))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("APPROVED"))
                .andExpect(jsonPath("$.verified_purchase").value(true))
                .andExpect(jsonPath("$.product_id").value(variant.getProduct().getId().intValue()))
                .andReturn();
        long reviewId = objectMapper.readTree(createdResult.getResponse().getContentAsString()).get("id").asLong();

        mockMvc.perform(post("/api/reviews")
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "order_item_id", orderItemId,
                                "rating", 4
                        ))))
                .andExpect(status().isConflict());

        mockMvc.perform(get("/api/products/{productId}/reviews", variant.getProduct().getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1));

        mockMvc.perform(patch("/admin/reviews/{reviewId}/moderate", reviewId)
                        .header("Authorization", "Bearer " + admin.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "status", "APPROVED",
                                "moderation_reason", "verified_purchase"
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("APPROVED"))
                .andExpect(jsonPath("$.moderated_by_user_account_id").value(admin.userId().intValue()));

        mockMvc.perform(get("/api/products/{productId}/reviews", variant.getProduct().getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].rating").value(5));

        mockMvc.perform(get("/api/products/{productId}/reviews/summary", variant.getProduct().getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.review_count").value(1))
                .andExpect(jsonPath("$.approved_review_count").value(1))
                .andExpect(jsonPath("$.average_rating").value(5.00))
                .andExpect(jsonPath("$.rating_5_count").value(1));

        ProductReviewSummary summary = productReviewSummaryRepository
                .findByProduct_Id(variant.getProduct().getId())
                .orElseThrow();
        assertThat(summary.getAverageRating()).isEqualByComparingTo("5.00");
        assertThat(summary.getApprovedReviewCount()).isEqualTo(1);
    }

    @Test
    void publicCanGetRecentReviews() throws Exception {
        ProductVariant variant = seedVariant("Phase15 Recent Review Shoe " + UUID.randomUUID(), 5);
        AuthSession user = registerCustomer();
        AuthSession admin = registerAdmin();
        CustomerAddress address = seedAddress(user.userId());

        long cartId = addToCart(user.accessToken(), variant.getId(), 1);
        JsonNode order = checkout(user.accessToken(), cartId, address.getId());
        long orderId = order.get("id").asLong();
        long orderItemId = order.get("items").get(0).get("id").asLong();
        long paymentId = createCodPayment(user.accessToken(), orderId, "recent-payment-" + UUID.randomUUID())
                .get("id")
                .asLong();
        confirmCodPayment(admin.accessToken(), paymentId, "recent-confirm-" + UUID.randomUUID());

        mockMvc.perform(post("/api/reviews")
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "order_item_id", orderItemId,
                                "rating", 4,
                                "title", "Nice",
                                "content", "Recent review comment"
                        ))))
                .andExpect(status().isCreated());

        mockMvc.perform(get("/api/reviews/recent")
                        .param("limit", "5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].content").value("Recent review comment"));
    }

    @Test
    void wishlistAddIsIdempotentByProductAndRemoveClearsItem() throws Exception {
        ProductVariant variant = seedVariant("Phase15 Wishlist Shoe " + UUID.randomUUID(), 5);
        AuthSession user = registerCustomer();

        mockMvc.perform(get("/api/wishlists/default")
                        .header("Authorization", "Bearer " + user.accessToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.default_wishlist").value(true))
                .andExpect(jsonPath("$.item_count").value(0));

        MvcResult firstAdd = mockMvc.perform(post("/api/wishlists/default/items")
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_id", variant.getProduct().getId(),
                                "product_variant_id", variant.getId(),
                                "note", "first save"
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(1))
                .andExpect(jsonPath("$.items.length()").value(1))
                .andReturn();
        JsonNode wishlist = objectMapper.readTree(firstAdd.getResponse().getContentAsString());
        long wishlistId = wishlist.get("id").asLong();
        long wishlistItemId = wishlist.get("items").get(0).get("id").asLong();

        mockMvc.perform(post("/api/wishlists/default/items")
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_id", variant.getProduct().getId(),
                                "product_variant_id", variant.getId(),
                                "note", "second save"
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(1))
                .andExpect(jsonPath("$.items.length()").value(1))
                .andExpect(jsonPath("$.items[0].note").value("second save"));

        assertThat(wishlistItemRepository.findByWishlist_IdOrderByCreatedAtDescIdDesc(wishlistId)).hasSize(1);

        mockMvc.perform(delete("/api/wishlists/items/{wishlistItemId}", wishlistItemId)
                        .header("Authorization", "Bearer " + user.accessToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(0))
                .andExpect(jsonPath("$.items.length()").value(0));

        mockMvc.perform(post("/api/wishlists/default/items")
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_id", variant.getProduct().getId(),
                                "product_variant_id", variant.getId()
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(1));

        mockMvc.perform(delete(
                        "/api/wishlists/default/items/products/{productId}",
                        variant.getProduct().getId()
                )
                        .header("Authorization", "Bearer " + user.accessToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.item_count").value(0));
    }

    private JsonNode createCodPayment(String accessToken, long orderId, String idempotencyKey) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/payments/cod")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "order_id", orderId,
                                "idempotency_key", idempotencyKey
                        ))))
                .andExpect(status().isOk())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode confirmCodPayment(String accessToken, long paymentId, String idempotencyKey) throws Exception {
        MvcResult result = mockMvc.perform(post("/admin/payments/{paymentId}/cod/confirm", paymentId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "idempotency_key", idempotencyKey,
                                "reason", "phase15_review_payment_confirm"
                        ))))
                .andExpect(status().isOk())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode checkout(String accessToken, long cartId, long addressId) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/checkout")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "cart_id", cartId,
                                "shipping_address_id", addressId
                        ))))
                .andExpect(status().isOk())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    private long addToCart(String accessToken, Long variantId, int quantity) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/cart/items")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_variant_id", variantId,
                                "quantity", quantity
                        ))))
                .andExpect(status().isOk())
                .andReturn();
        JsonNode cart = objectMapper.readTree(result.getResponse().getContentAsString());
        return cart.get("id").asLong();
    }

    private AuthSession registerAdmin() throws Exception {
        AuthSession admin = registerCustomer();
        UserRole role = userRoleRepository.findByName("ADMIN").orElseGet(() -> {
            UserRole newRole = new UserRole();
            newRole.setName("ADMIN");
            newRole.setDescription("Admin role");
            newRole.setActive(true);
            newRole.setCreatedAt(Instant.now());
            newRole.setUpdatedAt(Instant.now());
            return userRoleRepository.save(newRole);
        });
        UserAccount account = userAccountRepository.findByIdWithRoles(admin.userId()).orElseThrow();
        account.getRoles().add(role);
        account.setUpdatedAt(Instant.now());
        userAccountRepository.save(account);
        return admin;
    }

    private AuthSession registerCustomer() throws Exception {
        String email = "phase15-" + UUID.randomUUID() + "@example.test";
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "email", email,
                                "password", "Password123!",
                                "full_name", "Phase15 Test User"
                        ))))
                .andExpect(status().isCreated())
                .andReturn();
        JsonNode response = objectMapper.readTree(result.getResponse().getContentAsString());
        return new AuthSession(
                response.get("access_token").asText(),
                response.get("user").get("id").asLong()
        );
    }

    private CustomerAddress seedAddress(Long userAccountId) {
        Instant now = Instant.now();
        CustomerAddress address = new CustomerAddress();
        address.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
        address.setAddressType(CustomerAddressType.SHIPPING);
        address.setRecipientName("Phase15 Test User");
        address.setPhoneNumber("0900000000");
        address.setAddressLine1("15 Review Street");
        address.setAddressLine2("Floor 15");
        address.setWard("Ward 15");
        address.setDistrict("District 15");
        address.setCity("Ho Chi Minh City");
        address.setProvince("Ho Chi Minh");
        address.setCountryCode("VN");
        address.setPostalCode("70000");
        address.setDefaultAddress(true);
        address.setDeleted(false);
        address.setCreatedAt(now);
        address.setUpdatedAt(now);
        return customerAddressRepository.save(address);
    }

    private ProductVariant seedVariant(String title, int stock) {
        Instant now = Instant.now();
        Product product = new Product();
        product.setId(ThreadLocalRandom.current().nextLong(100_000_000L, 900_000_000L));
        product.setExternalId(product.getId() + 3_000_000);
        product.setArticleNumber("PHASE15-" + product.getId());
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setVariantName("Regular");
        product.setBrandName("Phase15 Brand");
        product.setGender("Unisex");
        product.setBaseColour("Black");
        product.setMainImage("https://cdn.test/phase15/" + product.getId() + "-main.jpg");
        product.setCatalogAddDate(now);
        product.setCreatedAt(now);
        product.setUpdatedAt(now);
        productRepository.save(product);

        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        variant.setSkuId(product.getId() + 60_000);
        variant.setOptionName("Size");
        variant.setOptionValue("M");
        variant.setUnifiedSize("M");
        variant.setInventoryCount(stock);
        variant.setAvailable(true);
        variant.setActive(true);
        variant.setCreatedAt(now);
        variant.setUpdatedAt(now);
        productVariantRepository.save(variant);

        ProductPrice productPrice = new ProductPrice();
        productPrice.setProduct(product);
        productPrice.setSellingPrice(new BigDecimal("150000.00"));
        productPrice.setImportPrice(null);
        productPrice.setVat(new BigDecimal("0.00"));
        productPrice.setCreatedAt(now);
        productPrice.setUpdatedAt(now);
        productPriceRepository.save(productPrice);

        ProductImage image = new ProductImage();
        image.setProduct(product);
        image.setImageType("MAIN");
        image.setImageUrl("https://cdn.test/phase15/" + product.getId() + ".jpg");
        image.setSortOrder(0);
        image.setCreatedAt(now);
        productImageRepository.save(image);
        return variant;
    }

    private record AuthSession(String accessToken, Long userId) {
    }
}
