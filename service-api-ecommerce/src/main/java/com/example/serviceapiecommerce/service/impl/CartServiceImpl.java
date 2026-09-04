package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.cart.CartItemAddRequest;
import com.example.serviceapiecommerce.dto.cart.CartItemResponse;
import com.example.serviceapiecommerce.dto.cart.CartItemUpdateRequest;
import com.example.serviceapiecommerce.dto.cart.CartResponse;
import com.example.serviceapiecommerce.entity.Cart;
import com.example.serviceapiecommerce.entity.CartItem;
import com.example.serviceapiecommerce.entity.CartStatus;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.CartItemRepository;
import com.example.serviceapiecommerce.repository.CartRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.CartService;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.function.Function;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class CartServiceImpl implements CartService {
    private static final String DEFAULT_CURRENCY = "VND";

    private final CartRepository cartRepository;
    private final CartItemRepository cartItemRepository;
    private final ProductVariantRepository productVariantRepository;
    private final ProductPriceRepository productPriceRepository;
    private final ProductImageRepository productImageRepository;
    private final UserAccountRepository userAccountRepository;

    public CartServiceImpl(
            CartRepository cartRepository,
            CartItemRepository cartItemRepository,
            ProductVariantRepository productVariantRepository,
            ProductPriceRepository productPriceRepository,
            ProductImageRepository productImageRepository,
            UserAccountRepository userAccountRepository
    ) {
        this.cartRepository = cartRepository;
        this.cartItemRepository = cartItemRepository;
        this.productVariantRepository = productVariantRepository;
        this.productPriceRepository = productPriceRepository;
        this.productImageRepository = productImageRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @Override
    @Transactional(readOnly = true)
    public CartResponse getCart(Long userAccountId) {
        return activeCart(userAccountId)
                .map(this::toResponse)
                .orElseGet(CartServiceImpl::emptyCartResponse);
    }

    @Override
    @Transactional
    public CartResponse addItem(Long userAccountId, CartItemAddRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "cart_item_request_required");
        }
        if (request.productVariantId() == null || request.quantity() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "cart_item_request_invalid");
        }

        ProductVariant variant = productVariantRepository.findByIdWithProduct(request.productVariantId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_variant_not_found"));
        int quantityToAdd = request.quantity();
        validateSellableQuantity(variant, quantityToAdd);

        Product product = variant.getProduct();
        ProductPrice price = currentPrice(product.getId());
        Cart cart = getOrCreateActiveCart(userAccountId);
        Instant now = Instant.now();
        CartItem item = cartItemRepository.findByCart_IdAndProductVariant_Id(cart.getId(), variant.getId())
                .orElseGet(() -> newCartItem(cart, product, variant, now));

        int newQuantity = quantityOf(item) + quantityToAdd;
        validateSellableQuantity(variant, newQuantity);
        item.setQuantity(newQuantity);
        item.setSelected(true);
        refreshPriceSnapshot(item, price);
        item.setUpdatedAt(now);
        cartItemRepository.save(item);
        touchCart(cart, now);

        return toResponse(cart);
    }

    @Override
    @Transactional
    public CartResponse updateItem(Long userAccountId, Long cartItemId, CartItemUpdateRequest request) {
        if (cartItemId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "cart_item_id_required");
        }
        if (request == null || (request.quantity() == null && request.selected() == null)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "cart_item_update_required");
        }

        CartItem item = activeCartItem(cartItemId, userAccountId);
        Instant now = Instant.now();
        if (request.quantity() != null) {
            validateSellableQuantity(item.getProductVariant(), request.quantity());
            refreshPriceSnapshot(item, currentPrice(item.getProduct().getId()));
            item.setQuantity(request.quantity());
        }
        if (request.selected() != null) {
            item.setSelected(request.selected());
        }
        item.setUpdatedAt(now);
        cartItemRepository.save(item);
        touchCart(item.getCart(), now);

        return toResponse(item.getCart());
    }

    @Override
    @Transactional
    public CartResponse removeItem(Long userAccountId, Long cartItemId) {
        if (cartItemId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "cart_item_id_required");
        }

        CartItem item = activeCartItem(cartItemId, userAccountId);
        Cart cart = item.getCart();
        Instant now = Instant.now();
        cartItemRepository.delete(item);
        touchCart(cart, now);

        return toResponse(cart);
    }

    private Cart getOrCreateActiveCart(Long userAccountId) {
        return cartRepository.findFirstByUserAccount_IdAndStatusOrderByUpdatedAtDescIdDesc(
                        userAccountId,
                        CartStatus.ACTIVE
                )
                .orElseGet(() -> {
                    Instant now = Instant.now();
                    Cart cart = new Cart();
                    cart.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
                    cart.setStatus(CartStatus.ACTIVE);
                    cart.setCurrency(DEFAULT_CURRENCY);
                    cart.setCreatedAt(now);
                    cart.setUpdatedAt(now);
                    return cartRepository.save(cart);
                });
    }

    private CartItem activeCartItem(Long cartItemId, Long userAccountId) {
        CartItem item = cartItemRepository.findByIdAndCart_UserAccount_Id(cartItemId, userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "cart_item_not_found"));
        if (item.getCart().getStatus() != CartStatus.ACTIVE) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "cart_item_not_found");
        }
        return item;
    }

    private CartItem newCartItem(Cart cart, Product product, ProductVariant variant, Instant now) {
        CartItem item = new CartItem();
        item.setCart(cart);
        item.setProduct(product);
        item.setProductVariant(variant);
        item.setQuantity(0);
        item.setSelected(true);
        item.setCurrency(DEFAULT_CURRENCY);
        item.setCreatedAt(now);
        item.setUpdatedAt(now);
        return item;
    }

    private void touchCart(Cart cart, Instant now) {
        cart.setUpdatedAt(now);
        cartRepository.save(cart);
    }

    private ProductPrice currentPrice(Long productId) {
        return productPriceRepository.findFirstByProduct_IdOrderByUpdatedAtDescIdDesc(productId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.CONFLICT, "product_price_missing"));
    }

    private static void refreshPriceSnapshot(CartItem item, ProductPrice price) {
        item.setAddedUnitPrice(price.getSellingPrice());
        item.setAddedDiscountedPrice(null);
        item.setAddedEffectivePrice(effectivePrice(price));
        item.setCurrency(DEFAULT_CURRENCY);
    }

    private static void validateSellableQuantity(ProductVariant variant, int quantity) {
        if (quantity <= 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_quantity");
        }
        if (!Boolean.TRUE.equals(variant.getActive()) || !Boolean.TRUE.equals(variant.getAvailable())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "product_variant_not_sellable");
        }
        Integer stock = variant.getInventoryCount();
        if (stock == null || stock <= 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "product_variant_out_of_stock");
        }
        if (quantity > stock) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "insufficient_stock");
        }
    }

    private CartResponse toResponse(Cart cart) {
        List<CartItem> items = sortedItems(cartItemRepository.findByCartIdWithProductData(cart.getId()));
        List<Long> productIds = items.stream()
                .map(item -> item.getProduct().getId())
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        Map<Long, ProductPrice> priceByProductId = latestPriceByProductId(
                productIds.isEmpty()
                        ? List.of()
                        : productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds)
        );
        Map<Long, List<ProductImage>> imagesByProductId = groupByProductId(
                productIds.isEmpty()
                        ? List.of()
                        : productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds),
                image -> image.getProduct().getId()
        );

        List<CartItemResponse> itemResponses = items.stream()
                .map(item -> toItemResponse(
                        item,
                        priceByProductId.get(item.getProduct().getId()),
                        imagesByProductId.getOrDefault(item.getProduct().getId(), List.of())
                ))
                .toList();

        BigDecimal subtotal = itemResponses.stream()
                .filter(item -> !Boolean.FALSE.equals(item.selected()))
                .map(CartItemResponse::lineSubtotal)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        int totalQuantity = itemResponses.stream()
                .map(CartItemResponse::quantity)
                .filter(Objects::nonNull)
                .reduce(0, Integer::sum);

        return new CartResponse(
                cart.getId(),
                cart.getStatus(),
                cart.getCurrency() == null ? DEFAULT_CURRENCY : cart.getCurrency(),
                itemResponses.size(),
                totalQuantity,
                subtotal,
                itemResponses,
                cart.getCreatedAt(),
                cart.getUpdatedAt()
        );
    }

    private static CartItemResponse toItemResponse(CartItem item, ProductPrice price, List<ProductImage> images) {
        Product product = item.getProduct();
        ProductVariant variant = item.getProductVariant();
        BigDecimal effectivePrice = effectivePrice(price);
        Integer quantity = quantityOf(item);
        BigDecimal lineSubtotal = effectivePrice == null
                ? null
                : effectivePrice.multiply(BigDecimal.valueOf(quantity));

        return new CartItemResponse(
                item.getId(),
                product.getId(),
                variant.getId(),
                variant.getSkuId(),
                product.getProductDisplayName(),
                product.getProductDisplayNameVi(),
                product.getBrandName(),
                variant.getOptionName(),
                variant.getOptionValue(),
                variant.getUnifiedSize(),
                quantity,
                !Boolean.FALSE.equals(item.getSelected()),
                variant.getInventoryCount(),
                isSellableForQuantity(variant, quantity),
                price == null ? null : price.getSellingPrice(),
                null,
                effectivePrice,
                lineSubtotal,
                item.getCurrency() == null ? DEFAULT_CURRENCY : item.getCurrency(),
                primaryImageUrl(product, images)
        );
    }

    private static CartResponse emptyCartResponse() {
        return new CartResponse(
                null,
                CartStatus.ACTIVE,
                DEFAULT_CURRENCY,
                0,
                0,
                BigDecimal.ZERO,
                List.of(),
                null,
                null
        );
    }

    private Optional<Cart> activeCart(Long userAccountId) {
        return cartRepository.findFirstByUserAccount_IdAndStatusOrderByUpdatedAtDescIdDesc(
                userAccountId,
                CartStatus.ACTIVE
        );
    }

    private static List<CartItem> sortedItems(Collection<CartItem> items) {
        return items.stream()
                .sorted(Comparator
                        .comparing(CartItem::getCreatedAt, Comparator.nullsLast(Comparator.naturalOrder()))
                        .thenComparing(CartItem::getId, Comparator.nullsLast(Comparator.naturalOrder())))
                .toList();
    }

    private static BigDecimal effectivePrice(ProductPrice price) {
        if (price == null) {
            return null;
        }
        return price.getSellingPrice();
    }

    private static boolean isSellableForQuantity(ProductVariant variant, int quantity) {
        return Boolean.TRUE.equals(variant.getActive())
                && Boolean.TRUE.equals(variant.getAvailable())
                && variant.getInventoryCount() != null
                && variant.getInventoryCount() >= quantity;
    }

    private static Integer quantityOf(CartItem item) {
        return item.getQuantity() == null ? 0 : item.getQuantity();
    }

    private static String primaryImageUrl(Product product, List<ProductImage> images) {
        return images.stream()
                .map(ProductImage::getImageUrl)
                .filter(CartServiceImpl::hasText)
                .findFirst()
                .orElse(product.getMainImage());
    }

    private static Map<Long, ProductPrice> latestPriceByProductId(Collection<ProductPrice> prices) {
        Map<Long, ProductPrice> latestByProductId = new LinkedHashMap<>();
        for (ProductPrice price : prices) {
            latestByProductId.putIfAbsent(price.getProduct().getId(), price);
        }
        return latestByProductId;
    }

    private static <T> Map<Long, List<T>> groupByProductId(
            Collection<T> values,
            Function<T, Long> productIdExtractor
    ) {
        Map<Long, List<T>> grouped = new LinkedHashMap<>();
        for (T value : values) {
            Long productId = productIdExtractor.apply(value);
            grouped.computeIfAbsent(productId, ignored -> new ArrayList<>()).add(value);
        }
        return grouped;
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
