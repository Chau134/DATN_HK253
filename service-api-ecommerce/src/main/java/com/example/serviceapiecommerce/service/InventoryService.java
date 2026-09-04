package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.inventory.InventoryAdjustmentRequest;
import com.example.serviceapiecommerce.dto.inventory.InventoryMovementResponse;
import com.example.serviceapiecommerce.entity.Order;
import com.example.serviceapiecommerce.entity.OrderItem;
import java.time.Instant;
import java.util.List;

public interface InventoryService {
    void reserveOrderStock(Order order, List<OrderItem> orderItems, Long userAccountId);

    void commitSale(Long orderId, Long changedByUserAccountId, String reason);

    void releaseOrCancelOrderStock(Long orderId, Long changedByUserAccountId, String reason);

    int expireActiveReservations(Instant now);

    InventoryMovementResponse adjustVariantStock(
            Long productVariantId,
            Long changedByUserAccountId,
            InventoryAdjustmentRequest request
    );
}
