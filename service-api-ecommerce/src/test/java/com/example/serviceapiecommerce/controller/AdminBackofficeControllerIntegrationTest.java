package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.entity.OrderStatusHistory;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserRole;
import com.example.serviceapiecommerce.repository.CategoryRepository;
import com.example.serviceapiecommerce.repository.CustomerAddressRepository;
import com.example.serviceapiecommerce.repository.OrderRepository;
import com.example.serviceapiecommerce.repository.OrderStatusHistoryRepository;
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
import java.util.List;
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
        "app.security.jwt.secret=test-secret-for-admin-backoffice-controller-integration-test-1234567890",
        "app.security.jwt.access-token-ttl-seconds=900",
        "app.security.jwt.refresh-token-ttl-days=30",
        "ai.service.enabled=false"
})
@AutoConfigureMockMvc
public class AdminBackofficeControllerIntegrationTest {
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
    private CategoryRepository categoryRepository;

    @Autowired
    private CustomerAddressRepository customerAddressRepository;

    @Autowired
    private UserAccountRepository userAccountRepository;

    @Autowired
    private UserRoleRepository userRoleRepository;

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private OrderStatusHistoryRepository orderStatusHistoryRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void customerCannotUseAdminBackofficeEndpoints() throws Exception {
        AuthSession customer = registerCustomer();

        mockMvc.perform(get("/admin/catalog/products")
                        .header("Authorization", "Bearer " + customer.accessToken()))
                .andExpect(status().isForbidden());

        mockMvc.perform(get("/admin/orders")
                        .header("Authorization", "Bearer " + customer.accessToken()))
                .andExpect(status().isForbidden());
    }

    @Test
    void adminCanManageCategoryProductVariantPriceAndImage() throws Exception {
        AuthSession admin = registerAdmin();
        long productId = ThreadLocalRandom.current().nextLong(100_000_000L, 900_000_000L);

        long categoryId = createCategory(admin.accessToken(), Map.of(
                "source_category_id", ThreadLocalRandom.current().nextLong(1_000_000L, 9_000_000L),
                "level", "style",
                "name", "Phase16 Shoes " + UUID.randomUUID(),
                "name_vi", "Giay Phase16",
                "active", true
        ));

        MvcResult createdProductResult = mockMvc.perform(post("/admin/catalog/products")
                        .header("Authorization", "Bearer " + admin.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(productRequest(
                                productId,
                                "Phase16 Admin Product " + UUID.randomUUID(),
                                List.of(categoryId)
                        ))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value((int) productId))
                .andExpect(jsonPath("$.category_ids[0]").value((int) categoryId))
                .andReturn();
        assertThat(productRepository.findById(productId)).isPresent();
        assertThat(objectMapper.readTree(createdProductResult.getResponse().getContentAsString()).get("variants"))
                .isEmpty();

        long variantId = createVariant(admin.accessToken(), productId, Map.of(
                "sku_id", productId + 70_000,
                "option_name", "Size",
                "option_value", "M",
                "unified_size", "M",
                "inventory_count", 12,
                "available", true,
                "active", true
        ));
        mockMvc.perform(post("/admin/catalog/products/{productId}/prices", productId)
                        .header("Authorization", "Bearer " + admin.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "selling_price", new BigDecimal("220000.00"),
                                "import_price", new BigDecimal("199000.00"),
                                "vat", new BigDecimal("0.00")
                        ))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.selling_price").value(220000.00));
        long imageId = addImage(admin.accessToken(), productId);

        mockMvc.perform(get("/admin/catalog/products/{productId}", productId)
                        .header("Authorization", "Bearer " + admin.accessToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.variants[0].id").value((int) variantId))
                .andExpect(jsonPath("$.prices[0].import_price").value(199000.00))
                .andExpect(jsonPath("$.images[0].id").value((int) imageId));

        mockMvc.perform(put("/admin/catalog/products/{productId}", productId)
                        .header("Authorization", "Bearer " + admin.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(productRequest(
                                productId,
                                "Phase16 Admin Product Updated",
                                List.of(categoryId)
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Phase16 Admin Product Updated"));

        mockMvc.perform(delete("/admin/catalog/categories/{categoryId}", categoryId)
                        .header("Authorization", "Bearer " + admin.accessToken()))
                .andExpect(status().isNoContent());
        assertThat(categoryRepository.findById(categoryId).orElseThrow().getIsActive()).isFalse();
    }

    @Test
    void adminOrderStatusTransitionsWriteHistory() throws Exception {
        ProductVariant variant = seedVariant("Phase16 Order Product " + UUID.randomUUID(), 3);
        AuthSession customer = registerCustomer();
        AuthSession admin = registerAdmin();
        CustomerAddress address = seedAddress(customer.userId());

        long cartId = addToCart(customer.accessToken(), variant.getId(), 1);
        long orderId = checkout(customer.accessToken(), cartId, address.getId()).get("id").asLong();
        
        // Directly transition order to PAID via repository to test admin order transitions starting from PAID
        Order order = orderRepository.findById(orderId).orElseThrow();
        order.setStatus(OrderStatus.PAID);
        orderRepository.save(order);
        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.PAID);

        mockMvc.perform(patch("/admin/orders/{orderId}/status", orderId)
                        .header("Authorization", "Bearer " + admin.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "status", "PACKING",
                                "reason", "admin_packing",
                                "note", "Packed by admin"
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PACKING"))
                .andExpect(jsonPath("$.admin_note").doesNotExist());

        mockMvc.perform(patch("/admin/orders/{orderId}/status", orderId)
                        .header("Authorization", "Bearer " + admin.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "status", "SHIPPING",
                                "reason", "admin_shipping"
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("SHIPPING"));

        List<OrderStatusHistory> history = orderStatusHistoryRepository.findByOrder_IdOrderByCreatedAtAscIdAsc(orderId);
        assertThat(history)
                .extracting(OrderStatusHistory::getToStatus)
                .contains(OrderStatus.PACKING, OrderStatus.SHIPPING);
        assertThat(history)
                .extracting(OrderStatusHistory::getReason)
                .contains("admin_packing", "admin_shipping");
    }

    private Map<String, Object> productRequest(Long productId, String title, List<Long> categoryIds) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("id", productId);
        request.put("external_id", productId + 4_000_000);
        request.put("article_number", "ADMIN-" + productId);
        request.put("title", title);
        request.put("title_vi", title + " vi");
        request.put("variant_name", "Regular");
        request.put("brand", "Phase16 Admin Brand");
        request.put("gender", "Unisex");
        request.put("base_colour", "Black");
        request.put("main_image", "https://cdn.test/admin/" + productId + "-main.jpg");
        request.put("description", "Phase16 admin product description");
        request.put("category_ids", categoryIds);
        return request;
    }

    private long createCategory(String accessToken, Map<String, Object> request) throws Exception {
        MvcResult result = mockMvc.perform(post("/admin/catalog/categories")
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(request)))
                .andExpect(status().isCreated())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asLong();
    }

    private long createVariant(String accessToken, long productId, Map<String, Object> request) throws Exception {
        MvcResult result = mockMvc.perform(post("/admin/catalog/products/{productId}/variants", productId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(request)))
                .andExpect(status().isCreated())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asLong();
    }

    private long addImage(String accessToken, long productId) throws Exception {
        MvcResult result = mockMvc.perform(post("/admin/catalog/products/{productId}/images", productId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "image_type", "MAIN",
                                "image_url", "https://cdn.test/admin/" + productId + ".jpg",
                                "sort_order", 0
                        ))))
                .andExpect(status().isCreated())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asLong();
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

    private void confirmCodPayment(String accessToken, long paymentId, String idempotencyKey) throws Exception {
        mockMvc.perform(post("/admin/payments/{paymentId}/cod/confirm", paymentId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "idempotency_key", idempotencyKey,
                                "reason", "phase16_cod_confirm"
                        ))))
                .andExpect(status().isOk());
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
        return objectMapper.readTree(result.getResponse().getContentAsString()).get("id").asLong();
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
        String email = "phase16-" + UUID.randomUUID() + "@example.test";
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "email", email,
                                "password", "Password123!",
                                "full_name", "Phase16 Test User"
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
        address.setRecipientName("Phase16 Test User");
        address.setPhoneNumber("0900000000");
        address.setAddressLine1("16 Admin Street");
        address.setCity("Ho Chi Minh City");
        address.setProvince("Ho Chi Minh");
        address.setCountryCode("VN");
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
        product.setExternalId(product.getId() + 5_000_000);
        product.setArticleNumber("PHASE16-" + product.getId());
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setVariantName("Regular");
        product.setBrandName("Phase16 Brand");
        product.setGender("Unisex");
        product.setBaseColour("Black");
        product.setMainImage("https://cdn.test/phase16/" + product.getId() + "-main.jpg");
        product.setCatalogAddDate(now);
        product.setCreatedAt(now);
        product.setUpdatedAt(now);
        productRepository.save(product);

        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        variant.setSkuId(product.getId() + 80_000);
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
        productPrice.setSellingPrice(new BigDecimal("160000.00"));
        productPrice.setImportPrice(null);
        productPrice.setVat(new BigDecimal("0.00"));
        productPrice.setCreatedAt(now);
        productPrice.setUpdatedAt(now);
        productPriceRepository.save(productPrice);

        ProductImage image = new ProductImage();
        image.setProduct(product);
        image.setImageType("MAIN");
        image.setImageUrl("https://cdn.test/phase16/" + product.getId() + ".jpg");
        image.setSortOrder(0);
        image.setCreatedAt(now);
        productImageRepository.save(image);
        return variant;
    }

    private record AuthSession(String accessToken, Long userId) {
    }
}
