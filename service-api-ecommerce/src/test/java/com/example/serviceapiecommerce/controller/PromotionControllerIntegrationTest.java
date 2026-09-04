package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.entity.Coupon;
import com.example.serviceapiecommerce.entity.CouponRedemption;
import com.example.serviceapiecommerce.entity.CouponRedemptionStatus;
import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserRole;
import com.example.serviceapiecommerce.repository.CouponRedemptionRepository;
import com.example.serviceapiecommerce.repository.CouponRepository;
import com.example.serviceapiecommerce.repository.CustomerAddressRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.repository.UserRoleRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.LinkedHashMap;
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
        "app.security.jwt.secret=test-secret-for-promotion-controller-integration-test-1234567890",
        "app.security.jwt.access-token-ttl-seconds=900",
        "app.security.jwt.refresh-token-ttl-days=30",
        "ai.service.enabled=false"
})
@AutoConfigureMockMvc
class PromotionControllerIntegrationTest {
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
    private CustomerAddressRepository customerAddressRepository;

    @Autowired
    private UserAccountRepository userAccountRepository;

    @Autowired
    private UserRoleRepository userRoleRepository;

    @Autowired
    private CouponRepository couponRepository;

    @Autowired
    private CouponRedemptionRepository couponRedemptionRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void checkoutAppliesCouponAndDoesNotDuplicateRedemptionForSameCart() throws Exception {
        AuthSession admin = registerAdmin();
        String code = "PHASE14-" + UUID.randomUUID();
        createCoupon(admin.accessToken(), couponRequest(code, "FIXED_AMOUNT", "10000.00", "0.00", null, null));

        ProductVariant variant = seedVariant("Phase14 Coupon " + UUID.randomUUID(), 5, new BigDecimal("100000.00"));
        AuthSession user = registerCustomer();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 2);

        JsonNode firstCheckout = checkout(user.accessToken(), cartId, address.getId(), code, status().isOk());
        long orderId = firstCheckout.get("id").asLong();
        assertThat(firstCheckout.get("discount_amount").decimalValue()).isEqualByComparingTo("10000.00");
        assertThat(firstCheckout.get("total_amount").decimalValue()).isEqualByComparingTo("190000.00");

        JsonNode repeatedCheckout = checkout(user.accessToken(), cartId, address.getId(), code, status().isOk());
        assertThat(repeatedCheckout.get("id").asLong()).isEqualTo(orderId);
        assertThat(couponRedemptionRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .hasSize(1)
                .extracting(CouponRedemption::getStatus)
                .containsExactly(CouponRedemptionStatus.APPLIED);
        Coupon coupon = couponRepository.findByCodeIgnoreCase(code).orElseThrow();
        assertThat(coupon.getUsedCount()).isEqualTo(1);
    }

    @Test
    void couponMinOrderAndExpiredCouponsFailWithConflict() throws Exception {
        AuthSession admin = registerAdmin();
        String minOrderCode = "MIN-" + UUID.randomUUID();
        createCoupon(admin.accessToken(), couponRequest(
                minOrderCode,
                "FIXED_AMOUNT",
                "10000.00",
                "500000.00",
                null,
                null
        ));
        String expiredCode = "EXP-" + UUID.randomUUID();
        Map<String, Object> expiredRequest = couponRequest(expiredCode, "FIXED_AMOUNT", "10000.00", "0.00", null, null);
        expiredRequest.put("starts_at", Instant.now().minusSeconds(172800).toString());
        expiredRequest.put("ends_at", Instant.now().minusSeconds(86400).toString());
        createCoupon(admin.accessToken(), expiredRequest);

        ProductVariant variant = seedVariant("Phase14 MinOrder " + UUID.randomUUID(), 5, new BigDecimal("100000.00"));
        AuthSession user = registerCustomer();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 1);

        checkout(user.accessToken(), cartId, address.getId(), minOrderCode, status().isConflict());

        mockMvc.perform(post("/api/coupons/validate")
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "code", expiredCode,
                                "order_amount", new BigDecimal("100000.00"),
                                "currency", "VND"
                        ))))
                .andExpect(status().isConflict());
    }

    @Test
    void couponUsageLimitBlocksSecondOrder() throws Exception {
        AuthSession admin = registerAdmin();
        String code = "LIMIT-" + UUID.randomUUID();
        createCoupon(admin.accessToken(), couponRequest(code, "FIXED_AMOUNT", "10000.00", "0.00", 1, null));

        ProductVariant variant = seedVariant("Phase14 UsageLimit " + UUID.randomUUID(), 10, new BigDecimal("100000.00"));
        AuthSession firstUser = registerCustomer();
        CustomerAddress firstAddress = seedAddress(firstUser.userId());
        long firstCartId = addToCart(firstUser.accessToken(), variant.getId(), 1);
        checkout(firstUser.accessToken(), firstCartId, firstAddress.getId(), code, status().isOk());

        AuthSession secondUser = registerCustomer();
        CustomerAddress secondAddress = seedAddress(secondUser.userId());
        long secondCartId = addToCart(secondUser.accessToken(), variant.getId(), 1);
        checkout(secondUser.accessToken(), secondCartId, secondAddress.getId(), code, status().isConflict());

        Coupon coupon = couponRepository.findByCodeIgnoreCase(code).orElseThrow();
        assertThat(coupon.getUsedCount()).isEqualTo(1);
        assertThat(couponRedemptionRepository.findByCoupon_IdOrderByCreatedAtDescIdDesc(coupon.getId())).hasSize(1);
    }

    @Test
    void couponPerUserLimitBlocksSecondOrderForSameUser() throws Exception {
        AuthSession admin = registerAdmin();
        String code = "PERUSER-" + UUID.randomUUID();
        createCoupon(admin.accessToken(), couponRequest(code, "FIXED_AMOUNT", "10000.00", "0.00", null, 1));

        ProductVariant variant = seedVariant("Phase14 PerUser " + UUID.randomUUID(), 10, new BigDecimal("100000.00"));
        AuthSession user = registerCustomer();
        CustomerAddress address = seedAddress(user.userId());
        long firstCartId = addToCart(user.accessToken(), variant.getId(), 1);
        checkout(user.accessToken(), firstCartId, address.getId(), code, status().isOk());

        long secondCartId = addToCart(user.accessToken(), variant.getId(), 1);
        checkout(user.accessToken(), secondCartId, address.getId(), code, status().isConflict());

        Coupon coupon = couponRepository.findByCodeIgnoreCase(code).orElseThrow();
        assertThat(couponRedemptionRepository.findByUserAccount_IdOrderByCreatedAtDescIdDesc(user.userId()).stream()
                .filter(redemption -> redemption.getCoupon().getId().equals(coupon.getId())))
                .hasSize(1);
    }

    @Test
    void automaticProductPromotionDiscountIsSnapshottedOnOrderItems() throws Exception {
        AuthSession admin = registerAdmin();
        ProductVariant variant = seedVariant("Phase14 ProductPromo " + UUID.randomUUID(), 5, new BigDecimal("100000.00"));
        long promotionId = createPromotion(admin.accessToken(), Map.of(
                "name", "Phase14 Product Promotion " + UUID.randomUUID(),
                "discount_type", "PERCENTAGE",
                "discount_value", new BigDecimal("10.00"),
                "max_discount_amount", new BigDecimal("50000.00"),
                "min_order_amount", new BigDecimal("0.00"),
                "currency", "VND",
                "status", "ACTIVE",
                "priority", 100,
                "stackable", false,
                "customer_scope", "ALL"
        ));
        addPromotionProduct(admin.accessToken(), promotionId, variant.getProduct().getId());

        AuthSession user = registerCustomer();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 2);

        mockMvc.perform(post("/api/checkout")
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "cart_id", cartId,
                                "shipping_address_id", address.getId()
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.subtotal_amount").value(200000.00))
                .andExpect(jsonPath("$.discount_amount").value(20000.00))
                .andExpect(jsonPath("$.total_amount").value(180000.00))
                .andExpect(jsonPath("$.items[0].line_discount").value(20000.00))
                .andExpect(jsonPath("$.items[0].line_total").value(180000.00));
    }

    private Map<String, Object> couponRequest(
            String code,
            String discountType,
            String discountValue,
            String minOrderAmount,
            Integer usageLimit,
            Integer usageLimitPerUser
    ) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("code", code);
        request.put("name", "Coupon " + code);
        request.put("discount_type", discountType);
        request.put("discount_value", new BigDecimal(discountValue));
        request.put("min_order_amount", new BigDecimal(minOrderAmount));
        request.put("currency", "VND");
        request.put("status", "ACTIVE");
        request.put("customer_scope", "ALL");
        if (usageLimit != null) {
            request.put("usage_limit", usageLimit);
        }
        if (usageLimitPerUser != null) {
            request.put("usage_limit_per_user", usageLimitPerUser);
        }
        return request;
    }

    private long createCoupon(String accessToken, Map<String, Object> request) throws Exception {
        MvcResult result = mockMvc.perform(post("/admin/coupons")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(request)))
                .andExpect(status().isCreated())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asLong();
    }

    private long createPromotion(String accessToken, Map<String, Object> request) throws Exception {
        MvcResult result = mockMvc.perform(post("/admin/promotions")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(request)))
                .andExpect(status().isCreated())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asLong();
    }

    private void addPromotionProduct(String accessToken, long promotionId, long productId) throws Exception {
        mockMvc.perform(post("/admin/promotions/{promotionId}/products", promotionId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "product_id", productId,
                                "active", true
                        ))))
                .andExpect(status().isOk());
    }

    private JsonNode checkout(
            String accessToken,
            long cartId,
            long addressId,
            String couponCode,
            org.springframework.test.web.servlet.ResultMatcher expectedStatus
    ) throws Exception {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("cart_id", cartId);
        request.put("shipping_address_id", addressId);
        request.put("coupon_code", couponCode);
        MvcResult result = mockMvc.perform(post("/api/checkout")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(request)))
                .andExpect(expectedStatus)
                .andReturn();
        String body = result.getResponse().getContentAsString();
        return body == null || body.isBlank() ? objectMapper.createObjectNode() : objectMapper.readTree(body);
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
        String email = "promotion-" + UUID.randomUUID() + "@example.test";
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "email", email,
                                "password", "Password123!",
                                "full_name", "Promotion Test User"
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
        address.setRecipientName("Promotion Test User");
        address.setPhoneNumber("0900000000");
        address.setAddressLine1("14 Promotion Street");
        address.setAddressLine2("Floor 14");
        address.setWard("Ward 14");
        address.setDistrict("District 14");
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

    private ProductVariant seedVariant(String title, int stock, BigDecimal price) {
        Instant now = Instant.now();
        Product product = new Product();
        product.setId(ThreadLocalRandom.current().nextLong(100_000_000L, 900_000_000L));
        product.setExternalId(product.getId() + 1_000_000);
        product.setArticleNumber("PROMO-" + product.getId());
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setVariantName("Regular");
        product.setBrandName("Phase14 Promotion Brand");
        product.setGender("Unisex");
        product.setBaseColour("Black");
        product.setMainImage("https://cdn.test/promotion/" + product.getId() + "-main.jpg");
        product.setCatalogAddDate(now);
        product.setCreatedAt(now);
        product.setUpdatedAt(now);
        productRepository.save(product);

        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        variant.setSkuId(product.getId() + 40_000);
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
        productPrice.setSellingPrice(price);
        productPrice.setImportPrice(null);
        productPrice.setVat(new BigDecimal("0.00"));
        productPrice.setCreatedAt(now);
        productPrice.setUpdatedAt(now);
        productPriceRepository.save(productPrice);

        ProductImage image = new ProductImage();
        image.setProduct(product);
        image.setImageType("MAIN");
        image.setImageUrl("https://cdn.test/promotion/" + product.getId() + ".jpg");
        image.setSortOrder(0);
        image.setCreatedAt(now);
        productImageRepository.save(image);
        return variant;
    }

    private record AuthSession(String accessToken, Long userId) {
    }
}
