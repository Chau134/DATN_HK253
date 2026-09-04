package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.inventory.InventoryAdjustmentRequest;
import com.example.serviceapiecommerce.dto.inventory.InventoryMovementResponse;
import com.example.serviceapiecommerce.entity.InventoryMovement;
import com.example.serviceapiecommerce.entity.InventoryMovementType;
import com.example.serviceapiecommerce.entity.InventoryReservation;
import com.example.serviceapiecommerce.entity.InventoryReservationStatus;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderItem;
import com.example.serviceapiecommerce.entity.ProductVariant;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.repository.InventoryMovementRepository;
import com.example.serviceapiecommerce.repository.InventoryReservationRepository;
import com.example.serviceapiecommerce.repository.OrderItemRepository;
import com.example.serviceapiecommerce.repository.OrderRepository;
import com.example.serviceapiecommerce.repository.ProductVariantRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.InventoryService;
import java.time.Duration;
import java.time.Instant;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.List;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class InventoryServiceImpl implements InventoryService {
    private static final String REF_ORDER = "ORDER";
    private static final String REF_ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT";
    private static final EnumSet<InventoryReservationStatus> RELEASABLE_OR_RESTORABLE_STATUSES =
            EnumSet.of(InventoryReservationStatus.ACTIVE, InventoryReservationStatus.CONSUMED);

    private final InventoryReservationRepository inventoryReservationRepository;
    private final InventoryMovementRepository inventoryMovementRepository;
    private final ProductVariantRepository productVariantRepository;
    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final UserAccountRepository userAccountRepository;
    private final Duration reservationTtl;

    public InventoryServiceImpl(
            InventoryReservationRepository inventoryReservationRepository,
            InventoryMovementRepository inventoryMovementRepository,
            ProductVariantRepository productVariantRepository,
            OrderRepository orderRepository,
            OrderItemRepository orderItemRepository,
            UserAccountRepository userAccountRepository,
            @Value("${app.inventory.reservation-ttl-minutes:30}") long reservationTtlMinutes
    ) {
        this.inventoryReservationRepository = inventoryReservationRepository;
        this.inventoryMovementRepository = inventoryMovementRepository;
        this.productVariantRepository = productVariantRepository;
        this.orderRepository = orderRepository;
        this.orderItemRepository = orderItemRepository;
        this.userAccountRepository = userAccountRepository;
        this.reservationTtl = Duration.ofMinutes(reservationTtlMinutes);
    }

    @Override
    @Transactional
    public void reserveOrderStock(Order order, List<OrderItem> orderItems, Long userAccountId) {
        if (order == null || order.getId() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "order_required");
        }
        if (orderItems == null || orderItems.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "order_items_required");
        }

        Instant now = Instant.now();
        for (OrderItem orderItem : sortedItems(orderItems)) {
            String reservationKey = reservationKey(order.getId(), orderItem.getSourceProductVariantId());
            Optional<InventoryReservation> existing = inventoryReservationRepository.findByReservationKey(reservationKey);
            if (existing.isPresent()) {
                InventoryReservation reservation = existing.get();
                if (reservation.getStatus() == InventoryReservationStatus.ACTIVE
                        || reservation.getStatus() == InventoryReservationStatus.CONSUMED) {
                    continue;
                }
                throw new ResponseStatusException(HttpStatus.CONFLICT, "inventory_reservation_not_active");
            }

            ProductVariant variant = lockedVariant(orderItem.getSourceProductVariantId());
            validateSellable(variant);
            int quantity = positiveQuantity(orderItem.getQuantity());
            int availableBefore = availableToReserve(variant);
            if (quantity > availableBefore) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "insufficient_stock");
            }

            InventoryReservation reservation = new InventoryReservation();
            reservation.setProduct(variant.getProduct());
            reservation.setProductVariant(variant);
            reservation.setUserAccount(userAccountRepository.getReferenceById(userAccountId));
            reservation.setCart(order.getCart());
            reservation.setOrder(order);
            reservation.setReservationKey(reservationKey);
            reservation.setQuantity(quantity);
            reservation.setStatus(InventoryReservationStatus.ACTIVE);
            reservation.setReservedAt(now);
            reservation.setExpiresAt(now.plus(reservationTtl));
            reservation.setCreatedAt(now);
            reservation.setUpdatedAt(now);
            InventoryReservation savedReservation = inventoryReservationRepository.save(reservation);

            saveMovementIfAbsent(newMovement(
                    InventoryMovementType.RESERVE,
                    -quantity,
                    availableBefore,
                    availableBefore - quantity,
                    savedReservation,
                    order,
                    orderItem,
                    changedBy(userAccountId),
                    REF_ORDER,
                    order.getOrderNumber(),
                    "reserve:" + reservationKey,
                    "checkout_reserved",
                    null,
                    now
            ));
        }
    }

    @Override
    @Transactional
    public void commitSale(Long orderId, Long changedByUserAccountId, String reason) {
        Order order = order(orderId);
        List<InventoryReservation> reservations = inventoryReservationRepository
                .findByOrder_IdOrderByCreatedAtDescIdDesc(orderId)
                .stream()
                .sorted(Comparator.comparing(reservation -> reservation.getProductVariant().getId()))
                .toList();
        if (reservations.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "inventory_reservation_not_found");
        }

        Instant now = Instant.now();
        for (InventoryReservation reservation : reservations) {
            if (reservation.getStatus() == InventoryReservationStatus.CONSUMED) {
                continue;
            }
            if (reservation.getStatus() != InventoryReservationStatus.ACTIVE) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "inventory_reservation_not_active");
            }

            ProductVariant variant = lockedVariant(reservation.getProductVariant().getId());
            int quantity = positiveQuantity(reservation.getQuantity());
            int before = stockOf(variant);
            if (quantity > before) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "insufficient_stock");
            }
            int after = before - quantity;
            variant.setInventoryCount(after);
            variant.setUpdatedAt(now);
            productVariantRepository.save(variant);

            reservation.setStatus(InventoryReservationStatus.CONSUMED);
            reservation.setConsumedAt(now);
            reservation.setUpdatedAt(now);
            inventoryReservationRepository.save(reservation);

            OrderItem orderItem = orderItemForReservation(orderId, reservation.getProductVariant().getId()).orElse(null);
            saveMovementIfAbsent(newMovement(
                    InventoryMovementType.COMMIT_SALE,
                    -quantity,
                    before,
                    after,
                    reservation,
                    order,
                    orderItem,
                    changedBy(changedByUserAccountId),
                    REF_ORDER,
                    order.getOrderNumber(),
                    "commit-sale:" + reservation.getReservationKey(),
                    blankToDefault(reason, "sale_committed"),
                    null,
                    now
            ));
        }
    }

    @Override
    @Transactional
    public void releaseOrCancelOrderStock(Long orderId, Long changedByUserAccountId, String reason) {
        Order order = order(orderId);
        List<InventoryReservation> reservations = inventoryReservationRepository
                .findByOrder_IdAndStatusInOrderByCreatedAtAscIdAsc(orderId, RELEASABLE_OR_RESTORABLE_STATUSES)
                .stream()
                .sorted(Comparator.comparing(reservation -> reservation.getProductVariant().getId()))
                .toList();
        if (reservations.isEmpty()) {
            return;
        }

        Instant now = Instant.now();
        for (InventoryReservation reservation : reservations) {
            if (reservation.getStatus() == InventoryReservationStatus.ACTIVE) {
                cancelActiveReservation(order, reservation, changedByUserAccountId, blankToDefault(reason, "order_cancelled"), now);
            } else if (reservation.getStatus() == InventoryReservationStatus.CONSUMED) {
                restoreConsumedReservation(order, reservation, changedByUserAccountId, blankToDefault(reason, "order_cancelled"), now);
            }
        }
    }

    @Override
    @Transactional
    public int expireActiveReservations(Instant now) {
        Instant resolvedNow = now == null ? Instant.now() : now;
        List<InventoryReservation> reservations = inventoryReservationRepository
                .findByStatusAndExpiresAtBeforeOrderByExpiresAtAscIdAsc(
                        InventoryReservationStatus.ACTIVE,
                        resolvedNow
                );

        int expiredCount = 0;
        for (InventoryReservation reservation : reservations) {
            if (reservation.getStatus() != InventoryReservationStatus.ACTIVE) {
                continue;
            }
            ProductVariant variant = lockedVariant(reservation.getProductVariant().getId());
            int availableBefore = availableToReserve(variant);
            int quantity = positiveQuantity(reservation.getQuantity());

            reservation.setStatus(InventoryReservationStatus.EXPIRED);
            reservation.setReleasedAt(resolvedNow);
            reservation.setReleaseReason("reservation_expired");
            reservation.setUpdatedAt(resolvedNow);
            inventoryReservationRepository.save(reservation);

            saveMovementIfAbsent(newMovement(
                    InventoryMovementType.RELEASE_RESERVATION,
                    quantity,
                    availableBefore,
                    availableBefore + quantity,
                    reservation,
                    reservation.getOrder(),
                    null,
                    null,
                    REF_ORDER,
                    reservation.getOrder() == null ? null : reservation.getOrder().getOrderNumber(),
                    "expire-reservation:" + reservation.getReservationKey(),
                    "reservation_expired",
                    null,
                    resolvedNow
            ));
            expiredCount++;
        }
        return expiredCount;
    }

    @Override
    @Transactional
    public InventoryMovementResponse adjustVariantStock(
            Long productVariantId,
            Long changedByUserAccountId,
            InventoryAdjustmentRequest request
    ) {
        if (request == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "inventory_adjustment_request_required");
        }
        int delta = request.quantityDelta() == null ? 0 : request.quantityDelta();
        if (delta == 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "quantity_delta_required");
        }
        String idempotencyKey = blankToNull(request.idempotencyKey());
        if (idempotencyKey != null) {
            Optional<InventoryMovement> existing = inventoryMovementRepository.findByIdempotencyKey(idempotencyKey);
            if (existing.isPresent()) {
                return toResponse(existing.get());
            }
        }

        ProductVariant variant = lockedVariant(productVariantId);
        int before = stockOf(variant);
        int after = before + delta;
        if (after < 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "insufficient_stock");
        }

        Instant now = Instant.now();
        variant.setInventoryCount(after);
        variant.setUpdatedAt(now);
        productVariantRepository.save(variant);

        InventoryMovement movement = saveMovementIfAbsent(newMovement(
                InventoryMovementType.ADJUSTMENT,
                delta,
                before,
                after,
                variant,
                changedBy(changedByUserAccountId),
                REF_ADMIN_ADJUSTMENT,
                String.valueOf(productVariantId),
                idempotencyKey,
                blankToDefault(request.reason(), "admin_adjustment"),
                blankToNull(request.note()),
                now
        ));
        return toResponse(movement);
    }

    private void cancelActiveReservation(
            Order order,
            InventoryReservation reservation,
            Long changedByUserAccountId,
            String reason,
            Instant now
    ) {
        ProductVariant variant = lockedVariant(reservation.getProductVariant().getId());
        int quantity = positiveQuantity(reservation.getQuantity());
        int availableBefore = availableToReserve(variant);
        reservation.setStatus(InventoryReservationStatus.CANCELLED);
        reservation.setReleasedAt(now);
        reservation.setReleaseReason(reason);
        reservation.setUpdatedAt(now);
        inventoryReservationRepository.save(reservation);

        saveMovementIfAbsent(newMovement(
                InventoryMovementType.RELEASE_RESERVATION,
                quantity,
                availableBefore,
                availableBefore + quantity,
                reservation,
                order,
                orderItemForReservation(order.getId(), reservation.getProductVariant().getId()).orElse(null),
                changedBy(changedByUserAccountId),
                REF_ORDER,
                order.getOrderNumber(),
                "release-reservation:" + reservation.getReservationKey(),
                reason,
                null,
                now
        ));
    }

    private void restoreConsumedReservation(
            Order order,
            InventoryReservation reservation,
            Long changedByUserAccountId,
            String reason,
            Instant now
    ) {
        ProductVariant variant = lockedVariant(reservation.getProductVariant().getId());
        int quantity = positiveQuantity(reservation.getQuantity());
        int before = stockOf(variant);
        int after = before + quantity;
        variant.setInventoryCount(after);
        variant.setUpdatedAt(now);
        productVariantRepository.save(variant);

        reservation.setStatus(InventoryReservationStatus.CANCELLED);
        reservation.setReleasedAt(now);
        reservation.setReleaseReason(reason);
        reservation.setUpdatedAt(now);
        inventoryReservationRepository.save(reservation);

        saveMovementIfAbsent(newMovement(
                InventoryMovementType.CANCEL_SALE,
                quantity,
                before,
                after,
                reservation,
                order,
                orderItemForReservation(order.getId(), reservation.getProductVariant().getId()).orElse(null),
                changedBy(changedByUserAccountId),
                REF_ORDER,
                order.getOrderNumber(),
                "cancel-sale:" + reservation.getReservationKey(),
                reason,
                null,
                now
        ));
    }

    private ProductVariant lockedVariant(Long productVariantId) {
        if (productVariantId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "product_variant_id_required");
        }
        return productVariantRepository.findByIdForUpdate(productVariantId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "product_variant_not_found"));
    }

    private Order order(Long orderId) {
        if (orderId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "order_id_required");
        }
        return orderRepository.findById(orderId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order_not_found"));
    }

    private Optional<OrderItem> orderItemForReservation(Long orderId, Long productVariantId) {
        return orderItemRepository.findByOrder_IdOrderByIdAsc(orderId).stream()
                .filter(item -> productVariantId.equals(item.getSourceProductVariantId()))
                .findFirst();
    }

    private int availableToReserve(ProductVariant variant) {
        int stock = stockOf(variant);
        Long activeReservations = inventoryReservationRepository.sumQuantityByProductVariantIdAndStatus(
                variant.getId(),
                InventoryReservationStatus.ACTIVE
        );
        return stock - (activeReservations == null ? 0 : activeReservations.intValue());
    }

    private static void validateSellable(ProductVariant variant) {
        if (!Boolean.TRUE.equals(variant.getActive()) || !Boolean.TRUE.equals(variant.getAvailable())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "product_variant_not_sellable");
        }
    }

    private static int positiveQuantity(Integer quantity) {
        if (quantity == null || quantity <= 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "invalid_quantity");
        }
        return quantity;
    }

    private static int stockOf(ProductVariant variant) {
        return variant.getInventoryCount() == null ? 0 : variant.getInventoryCount();
    }

    private UserAccount changedBy(Long userAccountId) {
        return userAccountId == null ? null : userAccountRepository.getReferenceById(userAccountId);
    }

    private InventoryMovement saveMovementIfAbsent(InventoryMovement movement) {
        if (movement.getIdempotencyKey() != null) {
            Optional<InventoryMovement> existing = inventoryMovementRepository.findByIdempotencyKey(
                    movement.getIdempotencyKey()
            );
            if (existing.isPresent()) {
                return existing.get();
            }
        }
        return inventoryMovementRepository.save(movement);
    }

    private static InventoryMovement newMovement(
            InventoryMovementType movementType,
            int quantityDelta,
            int quantityBefore,
            int quantityAfter,
            InventoryReservation reservation,
            Order order,
            OrderItem orderItem,
            UserAccount changedByUser,
            String referenceType,
            String referenceId,
            String idempotencyKey,
            String reason,
            String note,
            Instant now
    ) {
        InventoryMovement movement = new InventoryMovement();
        movement.setProduct(reservation == null ? null : reservation.getProduct());
        movement.setProductVariant(reservation == null ? null : reservation.getProductVariant());
        if (reservation == null && orderItem != null) {
            movement.setProduct(orderItem.getProduct());
            movement.setProductVariant(orderItem.getProductVariant());
        }
        movement.setReservation(reservation);
        movement.setOrder(order);
        movement.setOrderItem(orderItem);
        movement.setChangedByUserAccount(changedByUser);
        movement.setMovementType(movementType);
        movement.setQuantityDelta(quantityDelta);
        movement.setQuantityBefore(quantityBefore);
        movement.setQuantityAfter(quantityAfter);
        movement.setReferenceType(referenceType);
        movement.setReferenceId(referenceId);
        movement.setIdempotencyKey(idempotencyKey);
        movement.setReason(reason);
        movement.setNote(note);
        movement.setCreatedAt(now);
        return movement;
    }

    private static InventoryMovement newMovement(
            InventoryMovementType movementType,
            int quantityDelta,
            int quantityBefore,
            int quantityAfter,
            ProductVariant variant,
            UserAccount changedByUser,
            String referenceType,
            String referenceId,
            String idempotencyKey,
            String reason,
            String note,
            Instant now
    ) {
        InventoryMovement movement = new InventoryMovement();
        movement.setProduct(variant.getProduct());
        movement.setProductVariant(variant);
        movement.setChangedByUserAccount(changedByUser);
        movement.setMovementType(movementType);
        movement.setQuantityDelta(quantityDelta);
        movement.setQuantityBefore(quantityBefore);
        movement.setQuantityAfter(quantityAfter);
        movement.setReferenceType(referenceType);
        movement.setReferenceId(referenceId);
        movement.setIdempotencyKey(idempotencyKey);
        movement.setReason(reason);
        movement.setNote(note);
        movement.setCreatedAt(now);
        return movement;
    }

    private static List<OrderItem> sortedItems(List<OrderItem> orderItems) {
        return orderItems.stream()
                .sorted(Comparator.comparing(OrderItem::getSourceProductVariantId))
                .toList();
    }

    private static String reservationKey(Long orderId, Long productVariantId) {
        return "order:" + orderId + ":variant:" + productVariantId;
    }

    private static InventoryMovementResponse toResponse(InventoryMovement movement) {
        return new InventoryMovementResponse(
                movement.getId(),
                movement.getProduct() == null ? null : movement.getProduct().getId(),
                movement.getProductVariant() == null ? null : movement.getProductVariant().getId(),
                movement.getMovementType(),
                movement.getQuantityDelta(),
                movement.getQuantityBefore(),
                movement.getQuantityAfter(),
                movement.getReferenceType(),
                movement.getReferenceId(),
                movement.getIdempotencyKey(),
                movement.getReason(),
                movement.getNote(),
                movement.getCreatedAt()
        );
    }

    private static String blankToDefault(String value, String defaultValue) {
        String resolved = blankToNull(value);
        return resolved == null ? defaultValue : resolved;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
