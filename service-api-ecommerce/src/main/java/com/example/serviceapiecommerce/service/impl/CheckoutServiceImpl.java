package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.order.CheckoutPreviewRequest;
import com.example.serviceapiecommerce.dto.order.CheckoutPreviewResponse;
import com.example.serviceapiecommerce.dto.order.CheckoutRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;
import com.example.serviceapiecommerce.entity.Cart;
import com.example.serviceapiecommerce.entity.CartItem;
import com.example.serviceapiecommerce.entity.CartStatus;
import com.example.serviceapiecommerce.entity.CustomerAddress;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderAddress;
import com.example.serviceapiecommerce.entity.OrderAddressType;
import com.example.serviceapiecommerce.entity.OrderItem;
import com.example.serviceapiecommerce.entity.OrderStatus;
import com.example.serviceapiecommerce.entity.OrderStatusHistory;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.ProductImage;
import com.example.serviceapiecommerce.entity.ProductPrice;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.repository.CartItemRepository;
import com.example.serviceapiecommerce.repository.CartRepository;
import com.example.serviceapiecommerce.repository.CustomerAddressRepository;
import com.example.serviceapiecommerce.repository.OrderAddressRepository;
import com.example.serviceapiecommerce.repository.OrderItemRepository;
import com.example.serviceapiecommerce.repository.OrderRepository;
import com.example.serviceapiecommerce.repository.OrderStatusHistoryRepository;
import com.example.serviceapiecommerce.repository.ProductImageRepository;
import com.example.serviceapiecommerce.repository.ProductPriceRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.CheckoutService;
import com.example.serviceapiecommerce.service.CouponService;
import com.example.serviceapiecommerce.service.InventoryService;
import com.example.serviceapiecommerce.service.PromotionService;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class CheckoutServiceImpl implements CheckoutService {
    private static final String DEFAULT_CURRENCY = "VND";
    private static final BigDecimal ZERO = BigDecimal.ZERO;

    private final CartRepository cartRepository;
    private final CartItemRepository cartItemRepository;
    private final CustomerAddressRepository customerAddressRepository;
    private final ProductPriceRepository productPriceRepository;
    private final ProductImageRepository productImageRepository;
    private final UserAccountRepository userAccountRepository;
    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final OrderAddressRepository orderAddressRepository;
    private final OrderStatusHistoryRepository orderStatusHistoryRepository;
    private final OrderNumberGenerator orderNumberGenerator;
    private final OrderResponseMapper orderResponseMapper;
    private final InventoryService inventoryService;
    private final PromotionService promotionService;
    private final CouponService couponService;

    public CheckoutServiceImpl(
            CartRepository cartRepository,
            CartItemRepository cartItemRepository,
            CustomerAddressRepository customerAddressRepository,
            ProductPriceRepository productPriceRepository,
            ProductImageRepository productImageRepository,
            UserAccountRepository userAccountRepository,
            OrderRepository orderRepository,
            OrderItemRepository orderItemRepository,
            OrderAddressRepository orderAddressRepository,
            OrderStatusHistoryRepository orderStatusHistoryRepository,
            OrderNumberGenerator orderNumberGenerator,
            OrderResponseMapper orderResponseMapper,
            InventoryService inventoryService,
            PromotionService promotionService,
            CouponService couponService
    ) {
        this.cartRepository = cartRepository;
        this.cartItemRepository = cartItemRepository;
        this.customerAddressRepository = customerAddressRepository;
        this.productPriceRepository = productPriceRepository;
        this.productImageRepository = productImageRepository;
        this.userAccountRepository = userAccountRepository;
        this.orderRepository = orderRepository;
        this.orderItemRepository = orderItemRepository;
        this.orderAddressRepository = orderAddressRepository;
        this.orderStatusHistoryRepository = orderStatusHistoryRepository;
        this.orderNumberGenerator = orderNumberGenerator;
        this.orderResponseMapper = orderResponseMapper;
        this.inventoryService = inventoryService;
        this.promotionService = promotionService;
        this.couponService = couponService;
    }

    @Override
    @Transactional
    public OrderResponse checkout(Long userAccountId, CheckoutRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "checkout_request_required");
        }
        if (request.shippingAddressId() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "shipping_address_id_required");
        }
        if (request.cartId() != null) {
            var existing = orderRepository.findByCart_IdAndUserAccount_Id(request.cartId(), userAccountId);
            if (existing.isPresent()) {
                return orderResponseMapper.toResponse(existing.get());
            }
        }

        Cart cart = resolveCart(userAccountId, request.cartId());
        var existing = orderRepository.findByCart_IdAndUserAccount_Id(cart.getId(), userAccountId);
        if (existing.isPresent()) {
            return orderResponseMapper.toResponse(existing.get());
        }
        if (cart.getStatus() != CartStatus.ACTIVE) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "cart_not_active");
        }

        List<CartItem> selectedItems = cartItemRepository.findByCartIdWithProductData(cart.getId()).stream()
                .filter(item -> !Boolean.FALSE.equals(item.getSelected()))
                .toList();
        if (selectedItems.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "cart_empty");
        }

        CustomerAddress shippingAddress = customerAddress(request.shippingAddressId(), userAccountId);
        CustomerAddress billingAddress = request.billingAddressId() == null
                ? null
                : customerAddress(request.billingAddressId(), userAccountId);

        List<Long> productIds = selectedItems.stream()
                .map(item -> item.getProduct().getId())
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        Map<Long, ProductPrice> priceByProductId = latestPriceByProductId(
                productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds)
        );
        Map<Long, List<ProductImage>> imagesByProductId = groupByProductId(
                productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds),
                image -> image.getProduct().getId()
        );

        Instant now = Instant.now();
        List<OrderItem> orderItems = new ArrayList<>();
        BigDecimal subtotal = ZERO;
        for (CartItem cartItem : selectedItems) {
            Product product = cartItem.getProduct();
            ProductVariant variant = cartItem.getProductVariant();
            ProductPrice price = priceByProductId.get(product.getId());
            if (price == null) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "product_price_missing");
            }
            validateSellableQuantity(variant, cartItem.getQuantity());

            OrderItem orderItem = toOrderItem(
                    cartItem,
                    price,
                    imagesByProductId.getOrDefault(product.getId(), List.of()),
                    now
            );
            orderItems.add(orderItem);
            subtotal = subtotal.add(orderItem.getLineSubtotal());
        }
        BigDecimal automaticDiscount = promotionService.applyAutomaticPromotions(
                userAccountId,
                orderItems,
                subtotal,
                DEFAULT_CURRENCY,
                now
        );

        Order order = new Order();
        order.setOrderNumber(orderNumberGenerator.nextOrderNumber());
        order.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
        order.setCart(cart);
        order.setStatus(OrderStatus.PENDING);
        order.setCurrency(DEFAULT_CURRENCY);
        order.setItemCount(orderItems.size());
        BigDecimal taxAmount = ZERO;
        for (OrderItem item : orderItems) {
            ProductPrice price = priceByProductId.get(item.getProduct().getId());
            BigDecimal vatPercent = (price != null && price.getVat() != null) ? price.getVat() : ZERO;
            BigDecimal itemTax = item.getLineTotal().multiply(vatPercent).divide(BigDecimal.valueOf(100), 2, java.math.RoundingMode.HALF_UP);
            taxAmount = taxAmount.add(itemTax);
        }

        order.setSubtotalAmount(subtotal);
        order.setDiscountAmount(automaticDiscount);
        order.setShippingFee(ZERO);
        order.setTaxAmount(taxAmount);
        order.setTotalAmount(subtotal.subtract(automaticDiscount).add(taxAmount).max(ZERO));
        order.setPlacedAt(now);
        order.setCustomerNote(blankToNull(request.customerNote()));
        order.setCreatedAt(now);
        order.setUpdatedAt(now);
        Order savedOrder = orderRepository.save(order);

        orderItems.forEach(item -> item.setOrder(savedOrder));
        List<OrderItem> savedOrderItems = orderItemRepository.saveAll(orderItems);
        orderAddressRepository.save(toOrderAddress(savedOrder, shippingAddress, OrderAddressType.SHIPPING, now));
        if (billingAddress != null) {
            orderAddressRepository.save(toOrderAddress(savedOrder, billingAddress, OrderAddressType.BILLING, now));
        }
        orderStatusHistoryRepository.save(initialStatusHistory(savedOrder, userAccountId, now));
        couponService.applyCouponToOrder(userAccountId, savedOrder, request.couponCode(), now);
        inventoryService.reserveOrderStock(savedOrder, savedOrderItems, userAccountId);

        cart.setStatus(CartStatus.CHECKED_OUT);
        cart.setCheckedOutAt(now);
        cart.setUpdatedAt(now);
        cartRepository.save(cart);

        return orderResponseMapper.toResponse(savedOrder);
    }

    @Override
    @Transactional(readOnly = true)
    public CheckoutPreviewResponse preview(Long userAccountId, CheckoutPreviewRequest request) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "checkout_request_required");
        }
        Cart cart = resolveCart(userAccountId, request.cartId());
        if (cart.getStatus() != CartStatus.ACTIVE) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "cart_not_active");
        }

        List<CartItem> selectedItems = cartItemRepository.findByCartIdWithProductData(cart.getId()).stream()
                .filter(item -> !Boolean.FALSE.equals(item.getSelected()))
                .toList();
        if (selectedItems.isEmpty()) {
            return new CheckoutPreviewResponse(ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, ZERO);
        }

        List<Long> productIds = selectedItems.stream()
                .map(item -> item.getProduct().getId())
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        Map<Long, ProductPrice> priceByProductId = latestPriceByProductId(
                productPriceRepository.findByProductIdInOrderByProductIdAndLatest(productIds)
        );
        Map<Long, List<ProductImage>> imagesByProductId = groupByProductId(
                productImageRepository.findByProductIdInOrderByProductIdAndSortOrder(productIds),
                image -> image.getProduct().getId()
        );

        Instant now = Instant.now();
        List<OrderItem> orderItems = new ArrayList<>();
        BigDecimal subtotal = ZERO;
        for (CartItem cartItem : selectedItems) {
            Product product = cartItem.getProduct();
            ProductPrice price = priceByProductId.get(product.getId());
            if (price == null) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "product_price_missing");
            }
            OrderItem orderItem = toOrderItem(
                    cartItem,
                    price,
                    imagesByProductId.getOrDefault(product.getId(), List.of()),
                    now
            );
            orderItems.add(orderItem);
            subtotal = subtotal.add(orderItem.getLineSubtotal());
        }

        BigDecimal automaticDiscount = promotionService.applyAutomaticPromotions(
                userAccountId,
                orderItems,
                subtotal,
                DEFAULT_CURRENCY,
                now
        );

        BigDecimal couponDiscount = ZERO;
        if (request.couponCode() != null && !request.couponCode().isBlank()) {
            try {
                var validationRes = couponService.validateCoupon(
                        userAccountId,
                        new com.example.serviceapiecommerce.dto.promotion.CouponValidationRequest(
                                request.couponCode(),
                                subtotal.subtract(automaticDiscount).max(ZERO),
                                ZERO,
                                DEFAULT_CURRENCY
                        )
                );
                couponDiscount = validationRes.discountAmount();
            } catch (Exception e) {
                // If coupon is invalid, we propagate the error so checkout preview displays it
                throw e;
            }
        }

        BigDecimal totalDiscount = automaticDiscount.add(couponDiscount);

        BigDecimal taxAmount = ZERO;
        for (OrderItem item : orderItems) {
            ProductPrice price = priceByProductId.get(item.getProduct().getId());
            BigDecimal vatPercent = (price != null && price.getVat() != null) ? price.getVat() : ZERO;
            BigDecimal itemTax = item.getLineTotal().multiply(vatPercent).divide(BigDecimal.valueOf(100), 2, java.math.RoundingMode.HALF_UP);
            taxAmount = taxAmount.add(itemTax);
        }

        BigDecimal totalAmount = subtotal.subtract(totalDiscount).add(taxAmount).max(ZERO);

        return new CheckoutPreviewResponse(
                subtotal,
                automaticDiscount,
                couponDiscount,
                totalDiscount,
                ZERO,
                taxAmount,
                totalAmount
        );
    }

    private Cart resolveCart(Long userAccountId, Long requestedCartId) {
        if (requestedCartId != null) {
            return cartRepository.findByIdAndUserAccount_Id(requestedCartId, userAccountId)
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "cart_not_found"));
        }
        return cartRepository.findFirstByUserAccount_IdAndStatusOrderByUpdatedAtDescIdDesc(
                        userAccountId,
                        CartStatus.ACTIVE
                )
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.CONFLICT, "cart_empty"));
    }

    private CustomerAddress customerAddress(Long addressId, Long userAccountId) {
        return customerAddressRepository.findByIdAndUserAccount_IdAndDeletedFalse(addressId, userAccountId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "customer_address_not_found"));
    }

    private static OrderItem toOrderItem(
            CartItem cartItem,
            ProductPrice price,
            List<ProductImage> images,
            Instant now
    ) {
        Product product = cartItem.getProduct();
        ProductVariant variant = cartItem.getProductVariant();
        BigDecimal effectivePrice = effectivePrice(price);
        int quantity = cartItem.getQuantity();
        BigDecimal lineSubtotal = effectivePrice.multiply(BigDecimal.valueOf(quantity));

        OrderItem item = new OrderItem();
        item.setProduct(product);
        item.setProductVariant(variant);
        item.setSourceProductId(product.getId());
        item.setSourceProductVariantId(variant.getId());
        item.setSkuId(variant.getSkuId());
        item.setProductTitle(product.getProductDisplayName());
        item.setProductTitleVi(product.getProductDisplayNameVi());
        item.setBrandName(product.getBrandName());
        item.setVariantName(product.getVariantName());
        item.setOptionName(variant.getOptionName());
        item.setOptionValue(variant.getOptionValue());
        item.setUnifiedSize(variant.getUnifiedSize());
        item.setImageUrl(primaryImageUrl(product, images));
        item.setQuantity(quantity);
        item.setUnitPrice(price.getSellingPrice());
        item.setDiscountedUnitPrice(null);
        item.setEffectiveUnitPrice(effectivePrice);
        item.setLineDiscount(ZERO);
        item.setLineSubtotal(lineSubtotal);
        item.setLineTotal(lineSubtotal);
        item.setCurrency(DEFAULT_CURRENCY);
        item.setCreatedAt(now);
        return item;
    }

    private static OrderAddress toOrderAddress(
            Order order,
            CustomerAddress source,
            OrderAddressType addressType,
            Instant now
    ) {
        OrderAddress address = new OrderAddress();
        address.setOrder(order);
        address.setSourceCustomerAddress(source);
        address.setAddressType(addressType);
        address.setRecipientName(source.getRecipientName());
        address.setPhoneNumber(source.getPhoneNumber());
        address.setAddressLine1(source.getAddressLine1());
        address.setAddressLine2(source.getAddressLine2());
        address.setWard(source.getWard());
        address.setDistrict(source.getDistrict());
        address.setCity(source.getCity());
        address.setProvince(source.getProvince());
        address.setCountryCode(source.getCountryCode() == null ? "VN" : source.getCountryCode());
        address.setPostalCode(source.getPostalCode());
        address.setCreatedAt(now);
        return address;
    }

    private OrderStatusHistory initialStatusHistory(Order order, Long userAccountId, Instant now) {
        OrderStatusHistory history = new OrderStatusHistory();
        history.setOrder(order);
        history.setToStatus(OrderStatus.PENDING);
        history.setChangedByUserAccount(userAccountRepository.getReferenceById(userAccountId));
        history.setReason("checkout_created");
        history.setCreatedAt(now);
        return history;
    }

    private static void validateSellableQuantity(ProductVariant variant, Integer quantity) {
        if (quantity == null || quantity <= 0) {
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

    private static BigDecimal effectivePrice(ProductPrice price) {
        return price.getSellingPrice();
    }

    private static String primaryImageUrl(Product product, List<ProductImage> images) {
        return images.stream()
                .map(ProductImage::getImageUrl)
                .filter(CheckoutServiceImpl::hasText)
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

    private static String blankToNull(String value) {
        return hasText(value) ? value.trim() : null;
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
