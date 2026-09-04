package com.example.serviceapiecommerce.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.example.serviceapiecommerce.entity.InventoryReservation;
import com.example.serviceapiecommerce.entity.InventoryReservationStatus;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.entity.PaymentStatus;
import com.example.serviceapiecommerce.entity.PaymentTransaction;
import com.example.serviceapiecommerce.entity.PaymentTransactionType;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.entity.UserRole;
import com.example.serviceapiecommerce.repository.CustomerAddressRepository;
import com.example.serviceapiecommerce.repository.InventoryReservationRepository;
import com.example.serviceapiecommerce.repository.OrderRepository;
import com.example.serviceapiecommerce.repository.PaymentTransactionRepository;
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
        "app.security.jwt.secret=test-secret-for-payment-controller-integration-test-1234567890",
        "app.security.jwt.access-token-ttl-seconds=900",
        "app.security.jwt.refresh-token-ttl-days=30",
        "ai.service.enabled=false"
})
@AutoConfigureMockMvc
class PaymentControllerIntegrationTest {
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
    private InventoryReservationRepository inventoryReservationRepository;

    @Autowired
    private PaymentTransactionRepository paymentTransactionRepository;

    @Autowired
    private OrderRepository orderRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void codPaymentIsIdempotentAndConfirmCommitsStock() throws Exception {
        ProductVariant variant = seedVariant("Payment Phase13 COD " + UUID.randomUUID(), 2);
        AuthSession user = registerCustomer();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 2);
        long orderId = checkout(user.accessToken(), cartId, address.getId()).get("id").asLong();

        String createKey = "cod-create-" + UUID.randomUUID();
        JsonNode createdPayment = createCodPayment(user.accessToken(), orderId, createKey);
        long paymentId = createdPayment.get("id").asLong();
        assertThat(createdPayment.get("status").asText()).isEqualTo(PaymentStatus.PENDING.name());
        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.CONFIRMED);

        JsonNode repeatedPayment = createCodPayment(user.accessToken(), orderId, createKey);
        assertThat(repeatedPayment.get("id").asLong()).isEqualTo(paymentId);

        AuthSession admin = registerAdmin();
        String confirmKey = "cod-confirm-" + UUID.randomUUID();
        JsonNode confirmedPayment = confirmCodPayment(admin.accessToken(), paymentId, confirmKey);
        assertThat(confirmedPayment.get("status").asText()).isEqualTo(PaymentStatus.AUTHORIZED.name());
        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.SHIPPING);
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isZero();
        assertThat(inventoryReservationRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .extracting(InventoryReservation::getStatus)
                .containsExactly(InventoryReservationStatus.CONSUMED);
        assertThat(paymentTransactionRepository.findByPayment_IdOrderByCreatedAtDescIdDesc(paymentId))
                .extracting(PaymentTransaction::getTransactionType)
                .contains(PaymentTransactionType.COD_CONFIRM);

        confirmCodPayment(admin.accessToken(), paymentId, confirmKey);
        assertThat(paymentTransactionRepository.findByPayment_IdOrderByCreatedAtDescIdDesc(paymentId).stream()
                .filter(transaction -> transaction.getTransactionType() == PaymentTransactionType.COD_CONFIRM))
                .hasSize(1);
    }

    @Test
    void cancelCodPaymentReleasesReservationAndCancelsOrder() throws Exception {
        ProductVariant variant = seedVariant("Payment Phase13 Cancel " + UUID.randomUUID(), 3);
        AuthSession user = registerCustomer();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 1);
        long orderId = checkout(user.accessToken(), cartId, address.getId()).get("id").asLong();
        long paymentId = createCodPayment(user.accessToken(), orderId, "cod-cancel-create-" + UUID.randomUUID())
                .get("id")
                .asLong();

        String cancelKey = "cod-cancel-" + UUID.randomUUID();
        JsonNode cancelledPayment = cancelPayment(user.accessToken(), paymentId, cancelKey);
        assertThat(cancelledPayment.get("status").asText()).isEqualTo(PaymentStatus.CANCELLED.name());
        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.CANCELLED);
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(3);
        assertThat(inventoryReservationRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .extracting(InventoryReservation::getStatus)
                .containsExactly(InventoryReservationStatus.CANCELLED);

        cancelPayment(user.accessToken(), paymentId, cancelKey);
        assertThat(paymentTransactionRepository.findByPayment_IdOrderByCreatedAtDescIdDesc(paymentId).stream()
                .filter(transaction -> transaction.getTransactionType() == PaymentTransactionType.CANCEL))
                .hasSize(1);
    }

    @Test
    void failPaymentCancelsOrderAndReleasesReservation() throws Exception {
        ProductVariant variant = seedVariant("Payment Phase13 Fail " + UUID.randomUUID(), 2);
        AuthSession user = registerCustomer();
        AuthSession admin = registerAdmin();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 1);
        long orderId = checkout(user.accessToken(), cartId, address.getId()).get("id").asLong();
        long paymentId = createCodPayment(user.accessToken(), orderId, "cod-fail-create-" + UUID.randomUUID())
                .get("id")
                .asLong();

        JsonNode failedPayment = failPayment(admin.accessToken(), paymentId, "cod-fail-" + UUID.randomUUID());
        assertThat(failedPayment.get("status").asText()).isEqualTo(PaymentStatus.FAILED.name());
        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.CANCELLED);
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(2);
        assertThat(inventoryReservationRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .extracting(InventoryReservation::getStatus)
                .containsExactly(InventoryReservationStatus.CANCELLED);
    }

    @Test
    void refundPaidPaymentRestoresCommittedStock() throws Exception {
        ProductVariant variant = seedVariant("Payment Phase13 Refund " + UUID.randomUUID(), 1);
        AuthSession user = registerCustomer();
        AuthSession admin = registerAdmin();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 1);
        long orderId = checkout(user.accessToken(), cartId, address.getId()).get("id").asLong();
        long paymentId = createCodPayment(user.accessToken(), orderId, "cod-refund-create-" + UUID.randomUUID())
                .get("id")
                .asLong();
        confirmCodPayment(admin.accessToken(), paymentId, "cod-refund-confirm-" + UUID.randomUUID());
        confirmReceived(user.accessToken(), orderId);
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isZero();

        String refundKey = "cod-refund-" + UUID.randomUUID();
        JsonNode refundedPayment = refundPayment(admin.accessToken(), paymentId, refundKey);
        assertThat(refundedPayment.get("status").asText()).isEqualTo(PaymentStatus.REFUNDED.name());
        assertThat(orderRepository.findById(orderId).orElseThrow().getStatus()).isEqualTo(OrderStatus.REFUNDED);
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(1);
        assertThat(inventoryReservationRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .extracting(InventoryReservation::getStatus)
                .containsExactly(InventoryReservationStatus.CANCELLED);

        refundPayment(admin.accessToken(), paymentId, refundKey);
        assertThat(paymentTransactionRepository.findByPayment_IdOrderByCreatedAtDescIdDesc(paymentId).stream()
                .filter(transaction -> transaction.getTransactionType() == PaymentTransactionType.REFUND))
                .hasSize(1);
    }

    @Test
    void webhookDuplicateIsIgnoredByProviderAndEventId() throws Exception {
        String eventId = "evt-" + UUID.randomUUID();
        JsonNode first = ingestWebhook(eventId);
        JsonNode second = ingestWebhook(eventId);

        assertThat(first.get("duplicate").asBoolean()).isFalse();
        assertThat(second.get("duplicate").asBoolean()).isTrue();
        assertThat(second.get("id").asLong()).isEqualTo(first.get("id").asLong());
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

    private JsonNode confirmReceived(String accessToken, long orderId) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/orders/{orderId}/received", orderId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON))
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
                                "reason", "test_cod_confirm"
                        ))))
                .andExpect(status().isOk())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode cancelPayment(String accessToken, long paymentId, String idempotencyKey) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/payments/{paymentId}/cancel", paymentId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "idempotency_key", idempotencyKey,
                                "reason", "test_payment_cancel"
                        ))))
                .andExpect(status().isOk())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode failPayment(String accessToken, long paymentId, String idempotencyKey) throws Exception {
        MvcResult result = mockMvc.perform(post("/admin/payments/{paymentId}/fail", paymentId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "idempotency_key", idempotencyKey,
                                "reason", "test_payment_failed",
                                "failure_code", "TEST_FAIL",
                                "failure_message", "Test failure"
                        ))))
                .andExpect(status().isOk())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode refundPayment(String accessToken, long paymentId, String idempotencyKey) throws Exception {
        MvcResult result = mockMvc.perform(post("/admin/payments/{paymentId}/refund", paymentId)
                        .header("Authorization", "Bearer " + accessToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "idempotency_key", idempotencyKey,
                                "reason", "test_payment_refund"
                        ))))
                .andExpect(status().isOk())
                .andReturn();
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    private JsonNode ingestWebhook(String eventId) throws Exception {
        MvcResult result = mockMvc.perform(post("/api/payments/webhooks/test-provider")
                        .header("X-Event-Id", eventId)
                        .header("X-Event-Type", "payment.updated")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"paid\"}"))
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
        String email = "payment-" + UUID.randomUUID() + "@example.test";
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "email", email,
                                "password", "Password123!",
                                "full_name", "Payment Test User"
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
        address.setRecipientName("Payment Test User");
        address.setPhoneNumber("0900000000");
        address.setAddressLine1("34 Payment Street");
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
        product.setExternalId(product.getId() + 2_000_000);
        product.setArticleNumber("PAYMENT-" + product.getId());
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setVariantName("Regular");
        product.setBrandName("Phase13 Payment Brand");
        product.setGender("Unisex");
        product.setBaseColour("Black");
        product.setMainImage("https://cdn.test/payment/" + product.getId() + "-main.jpg");
        product.setCatalogAddDate(now);
        product.setCreatedAt(now);
        product.setUpdatedAt(now);
        productRepository.save(product);

        ProductVariant variant = new ProductVariant();
        variant.setProduct(product);
        variant.setSkuId(product.getId() + 50_000);
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
        productPrice.setSellingPrice(new BigDecimal("120000.00"));
        productPrice.setImportPrice(null);
        productPrice.setVat(new BigDecimal("0.00"));
        productPrice.setCreatedAt(now);
        productPrice.setUpdatedAt(now);
        productPriceRepository.save(productPrice);

        ProductImage image = new ProductImage();
        image.setProduct(product);
        image.setImageType("MAIN");
        image.setImageUrl("https://cdn.test/payment/" + product.getId() + ".jpg");
        image.setSortOrder(0);
        image.setCreatedAt(now);
        productImageRepository.save(image);
        return variant;
    }

    private record AuthSession(String accessToken, Long userId) {
    }
}
