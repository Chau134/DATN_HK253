package com.example.serviceapiecommerce.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.serviceapiecommerce.dto.inventory.InventoryAdjustmentRequest;
import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.CustomerAddressType;
import com.example.serviceapiecommerce.entity.InventoryMovement;
import com.example.serviceapiecommerce.entity.InventoryMovementType;
import com.example.serviceapiecommerce.entity.InventoryReservation;
import com.example.serviceapiecommerce.entity.InventoryReservationStatus;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.CustomerAddressRepository;
import com.example.serviceapiecommerce.repository.InventoryMovementRepository;
import com.example.serviceapiecommerce.repository.InventoryReservationRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.InventoryService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Instant;
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
        "app.security.jwt.secret=test-secret-for-inventory-service-integration-test-1234567890",
        "app.security.jwt.access-token-ttl-seconds=900",
        "app.security.jwt.refresh-token-ttl-days=30",
        "ai.service.enabled=false"
})
@AutoConfigureMockMvc
class InventoryServiceIntegrationTest {
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
    private InventoryReservationRepository inventoryReservationRepository;

    @Autowired
    private InventoryMovementRepository inventoryMovementRepository;

    @Autowired
    private InventoryService inventoryService;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void checkoutReservationBlocksOversellAcrossCarts() throws Exception {
        ProductVariant variant = seedVariant(
                "Inventory Phase12 Oversell " + UUID.randomUUID(),
                2,
                new BigDecimal("100000.00")
        );

        AuthSession firstUser = registerCustomer();
        CustomerAddress firstAddress = seedAddress(firstUser.userId());
        long firstCartId = addToCart(firstUser.accessToken(), variant.getId(), 2);
        long firstOrderId = checkout(firstUser.accessToken(), firstCartId, firstAddress.getId())
                .get("id")
                .asLong();

        List<InventoryReservation> reservations = inventoryReservationRepository
                .findByOrder_IdAndStatusOrderByCreatedAtAscIdAsc(firstOrderId, InventoryReservationStatus.ACTIVE);
        assertThat(reservations).hasSize(1);
        assertThat(reservations.getFirst().getQuantity()).isEqualTo(2);
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(2);
        assertThat(inventoryMovementRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(firstOrderId))
                .extracting(InventoryMovement::getMovementType)
                .contains(InventoryMovementType.RESERVE);

        AuthSession secondUser = registerCustomer();
        CustomerAddress secondAddress = seedAddress(secondUser.userId());
        long secondCartId = addToCart(secondUser.accessToken(), variant.getId(), 1);
        mockMvc.perform(post("/api/checkout")
                        .header("Authorization", "Bearer " + secondUser.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "cart_id", secondCartId,
                                "shipping_address_id", secondAddress.getId()
                        ))))
                .andExpect(status().isConflict());
    }

    @Test
    void commitSaleIsIdempotentAndCancelRestoresCommittedStock() throws Exception {
        ProductVariant variant = seedVariant(
                "Inventory Phase12 Commit " + UUID.randomUUID(),
                3,
                new BigDecimal("90000.00")
        );
        AuthSession user = registerCustomer();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 2);
        long orderId = checkout(user.accessToken(), cartId, address.getId()).get("id").asLong();

        inventoryService.commitSale(orderId, user.userId(), "test_commit");
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(1);
        assertThat(inventoryReservationRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .extracting(InventoryReservation::getStatus)
                .containsExactly(InventoryReservationStatus.CONSUMED);
        assertThat(inventoryMovementRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .extracting(InventoryMovement::getMovementType)
                .contains(InventoryMovementType.COMMIT_SALE);

        inventoryService.commitSale(orderId, user.userId(), "test_commit");
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(1);
        assertThat(inventoryMovementRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId).stream()
                .filter(movement -> movement.getMovementType() == InventoryMovementType.COMMIT_SALE))
                .hasSize(1);

        mockMvc.perform(post("/api/orders/{orderId}/cancel", orderId)
                        .header("Authorization", "Bearer " + user.accessToken())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of("reason", "test_cancel"))))
                .andExpect(status().isOk());

        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(3);
        assertThat(inventoryReservationRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .extracting(InventoryReservation::getStatus)
                .containsExactly(InventoryReservationStatus.CANCELLED);
        assertThat(inventoryMovementRepository.findByOrder_IdOrderByCreatedAtDescIdDesc(orderId))
                .extracting(InventoryMovement::getMovementType)
                .contains(InventoryMovementType.CANCEL_SALE);
    }

    @Test
    void expiredReservationReleasesAvailabilityAndAdjustmentAuditsStockChange() throws Exception {
        ProductVariant variant = seedVariant(
                "Inventory Phase12 Expire " + UUID.randomUUID(),
                4,
                new BigDecimal("70000.00")
        );
        AuthSession user = registerCustomer();
        CustomerAddress address = seedAddress(user.userId());
        long cartId = addToCart(user.accessToken(), variant.getId(), 3);
        long orderId = checkout(user.accessToken(), cartId, address.getId()).get("id").asLong();

        InventoryReservation reservation = inventoryReservationRepository
                .findByOrder_IdAndStatusOrderByCreatedAtAscIdAsc(orderId, InventoryReservationStatus.ACTIVE)
                .getFirst();
        reservation.setExpiresAt(Instant.now().minusSeconds(1));
        inventoryReservationRepository.save(reservation);

        int expiredCount = inventoryService.expireActiveReservations(Instant.now());
        assertThat(expiredCount).isGreaterThanOrEqualTo(1);
        assertThat(inventoryReservationRepository.findById(reservation.getId()).orElseThrow().getStatus())
                .isEqualTo(InventoryReservationStatus.EXPIRED);
        assertThat(inventoryMovementRepository.findByReservation_IdOrderByCreatedAtDescIdDesc(reservation.getId()))
                .extracting(InventoryMovement::getMovementType)
                .contains(InventoryMovementType.RELEASE_RESERVATION);

        var adjustment = inventoryService.adjustVariantStock(
                variant.getId(),
                user.userId(),
                new InventoryAdjustmentRequest(5, "inventory-adjust-" + UUID.randomUUID(), "test_adjust", null)
        );
        assertThat(adjustment.movementType()).isEqualTo(InventoryMovementType.ADJUSTMENT);
        assertThat(adjustment.quantityBefore()).isEqualTo(4);
        assertThat(adjustment.quantityAfter()).isEqualTo(9);
        assertThat(productVariantRepository.findById(variant.getId()).orElseThrow().getInventoryCount()).isEqualTo(9);
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

    private AuthSession registerCustomer() throws Exception {
        String email = "inventory-" + UUID.randomUUID() + "@example.test";
        MvcResult result = mockMvc.perform(post("/api/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsBytes(Map.of(
                                "email", email,
                                "password", "Password123!",
                                "full_name", "Inventory Test User"
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
        address.setRecipientName("Inventory Test User");
        address.setPhoneNumber("0900000000");
        address.setAddressLine1("12 Inventory Street");
        address.setCity("Ho Chi Minh City");
        address.setProvince("Ho Chi Minh");
        address.setCountryCode("VN");
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
        product.setArticleNumber("INVENTORY-" + product.getId());
        product.setProductDisplayName(title);
        product.setProductDisplayNameVi(title + " vi");
        product.setVariantName("Regular");
        product.setBrandName("Phase12 Inventory Brand");
        product.setGender("Unisex");
        product.setBaseColour("Black");
        product.setMainImage("https://cdn.test/inventory/" + product.getId() + "-main.jpg");
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
        image.setImageUrl("https://cdn.test/inventory/" + product.getId() + ".jpg");
        image.setSortOrder(0);
        image.setCreatedAt(now);
        productImageRepository.save(image);
        return variant;
    }

    private record AuthSession(String accessToken, Long userId) {
    }
}
