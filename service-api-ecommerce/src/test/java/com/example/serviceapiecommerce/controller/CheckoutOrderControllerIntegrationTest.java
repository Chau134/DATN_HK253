package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserRole;
import com.example.serviceapiecommerce.repository.CustomerAddressRepository;
import com.example.serviceapiecommerce.repository.OrderRepository;
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
        "app.security.jwt.secret=test-secret-for-checkout-order-controller-integration-test-1234567890",
        "app.security.jwt.access-token-ttl-seconds=900",
        "app.security.jwt.refresh-token-ttl-days=30",
        "ai.service.enabled=false"
})
@AutoConfigureMockMvc
class CheckoutOrderControllerIntegrationTest {
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
    private OrderRepository orderRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void checkoutIsIdempotentForSameCartAndOrderKeepsSnapshots() throws Exception {
        String title = "Checkout Phase11 Shoe " + UUID.randomUUID();
        ProductVariant variant = seedVariant(
                title,
                true,
                true,
                10,
                new BigDecimal("100000.00"),
                new BigDecimal("80000.00")
        );
        AuthSession auth = registerCustomer();
        CustomerAddress address = seedAddress(auth.userId());
        long cartId = addToCart(auth.accessToken(), variant.getId(), 2);

        Map<String, Object> checkoutRequest = Map.of(
                "cart_id", cartId,
                "shipping_address_id", address.getId(),
                "customer_note", "Leave at reception"
        );
        MvcResult firstCheckout = mockMvc.perform(post("/api/checkout")
                        .header("Authorization", "Bearer " + auth.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(checkoutRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PENDING"))
                .andExpect(jsonPath("$.item_count").value(1))
                .andExpect(jsonPath("$.subtotal_amount").value(200000.00))
                .andExpect(jsonPath("$.total_amount").value(200000.00))
                .andExpect(jsonPath("$.customer_note").value("Leave at reception"))
                .andExpect(jsonPath("$.items[0].product_title").value(title))
                .andExpect(jsonPath("$.items[0].effective_unit_price").value(100000.00))
                .andExpect(jsonPath("$.items[0].line_total").value(200000.00))
                .andExpect(jsonPath("$.addresses[0].recipient_name").value("Checkout Test User"))
                .andExpect(jsonPath("$.status_history[0].to_status").value("PENDING"))
                .andReturn();
        JsonNode first = objectMapper.readTree(firstCheckout.getResponse().getContentAsString());
        long orderId = first.get("id").asLong();
        String orderNumber = first.get("order_number").asText();

        mockMvc.perform(post("/api/checkout")
                        .header("Authorization", "Bearer " + auth.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(checkoutRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value((int) orderId))
                .andExpect(jsonPath("$.order_number").value(orderNumber))
                .andExpect(jsonPath("$.items.length()").value(1));

        Product product = variant.getProduct();
        product.setProductDisplayName(title + " changed after order");
        product.setUpdatedAt(Instant.now().plusSeconds(60));
        productRepository.save(product);

        ProductPrice changedPrice = new ProductPrice();
        changedPrice.setProduct(product);
        changedPrice.setSellingPrice(new BigDecimal("150000.00"));
        changedPrice.setImportPrice(null);
        changedPrice.setVat(new BigDecimal("0.00"));
        changedPrice.setCreatedAt(Instant.now().plusSeconds(60));
        changedPrice.setUpdatedAt(Instant.now().plusSeconds(60));
        productPriceRepository.save(changedPrice);

        mockMvc.perform(get("/api/orders/{orderId}", orderId)
                        .header("Authorization", "Bearer " + auth.accessToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.order_number").value(orderNumber))
                .andExpect(jsonPath("$.items[0].product_title").value(title))
                .andExpect(jsonPath("$.items[0].effective_unit_price").value(100000.00))
                .andExpect(jsonPath("$.addresses[0].address_line1").value("11 Checkout Street"));

        MvcResult listOrders = mockMvc.perform(get("/api/orders")
                        .header("Authorization", "Bearer " + auth.accessToken()))
                .andExpect(status().isOk())
                .andReturn();
        JsonNode orders = objectMapper.readTree(listOrders.getResponse().getContentAsString());
        assertThat(orders.findValuesAsText("order_number")).contains(orderNumber);
    }

    @Test
    void cancelOrderUpdatesStatusAndWritesHistory() throws Exception {
        ProductVariant variant = seedVariant(
                "Checkout Phase11 Cancel " + UUID.randomUUID(),
                true,
                true,
                5,
                new BigDecimal("90000.00"),
                null
        );
        AuthSession auth = registerCustomer();
        CustomerAddress address = seedAddress(auth.userId());
        long cartId = addToCart(auth.accessToken(), variant.getId(), 1);
        long orderId = checkout(auth.accessToken(), cartId, address.getId()).get("id").asLong();

        mockMvc.perform(post("/api/orders/{orderId}/cancel", orderId)
                        .header("Authorization", "Bearer " + auth.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "reason", "changed_mind",
                                "note", "Customer requested cancellation"
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("CANCELLED"))
                .andExpect(jsonPath("$.cancelled_at").isString())
                .andExpect(jsonPath("$.status_history[0].to_status").value("PENDING"))
                .andExpect(jsonPath("$.status_history[1].from_status").value("PENDING"))
                .andExpect(jsonPath("$.status_history[1].to_status").value("CANCELLED"))
                .andExpect(jsonPath("$.status_history[1].reason").value("changed_mind"));
    }

    @Test
    void customerCanCompletePurchaseEndToEndWithCodConfirmation() throws Exception {
        ProductVariant variant = seedVariant(
                "Phase17 E2E Purchase " + UUID.randomUUID(),
                true,
                true,
                4,
                new BigDecimal("125000.00"),
                null
        );
        AuthSession customer = registerCustomer();
        AuthSession admin = registerAdmin();
        CustomerAddress address = seedAddress(customer.userId());
        long cartId = addToCart(customer.accessToken(), variant.getId(), 2);

        JsonNode checkedOutOrder = checkout(customer.accessToken(), cartId, address.getId());
        long orderId = checkedOutOrder.get("id").asLong();
        assertThat(checkedOutOrder.get("status").asText()).isEqualTo(OrderStatus.PENDING.name());

        JsonNode payment = createCodPayment(customer.accessToken(), orderId, "phase17-create-" + UUID.randomUUID());
        long paymentId = payment.get("id").asLong();
        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.CONFIRMED);

        mockMvc.perform(post("/admin/payments/{paymentId}/cod/confirm", paymentId)
                        .header("Authorization", "Bearer " + admin.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "idempotency_key", "phase17-confirm-" + UUID.randomUUID(),
                                "reason", "phase17_e2e_confirm"
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("AUTHORIZED"));

        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.SHIPPING);
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(2);

        mockMvc.perform(post("/api/orders/{orderId}/received", orderId)
                        .header("Authorization", "Bearer " + customer.accessToken())
                        .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("COMPLETED"));

        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.COMPLETED);

        mockMvc.perform(get("/api/orders/{orderId}", orderId)
                        .header("Authorization", "Bearer " + customer.accessToken()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("COMPLETED"))
                .andExpect(jsonPath("$.status_history[*].to_status").value(org.hamcrest.Matchers.hasItem("COMPLETED")));
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
        String email = "checkout-" + UUID.randomUUID() + "@example.test";
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "email", email,
                                "password", "Password123!",
                                "full_name", "Checkout Test User"
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
        address.setRecipientName("Checkout Test User");
        address.setPhoneNumber("0900000000");
        address.setAddressLine1("11 Checkout Street");
        address.setAddressLine2("Floor 2");
        address.setWard("Ward 1");
        address.setDistrict("District 1");
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
        product.setArticleNumber("CHECKOUT-" + product.getId());
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setVariantName("Regular");
        product.setBrandName("Phase11 Checkout Brand");
        product.setGender("Unisex");
        product.setBaseColour("Black");
        product.setMainImage("https://cdn.test/checkout/" + product.getId() + "-main.jpg");
        product.setCatalogAddDate(now);
        product.setCreatedAt(now);
        product.setUpdatedAt(now);
        productRepository.save(product);

        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        variant.setSkuId(product.getId() + 30_000);
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
        image.setImageUrl("https://cdn.test/checkout/" + product.getId() + ".jpg");
        image.setSortOrder(0);
        image.setCreatedAt(now);
        productImageRepository.save(image);
        return variant;
    }

    private record AuthSession(String accessToken, Long userId) {
    }
}
