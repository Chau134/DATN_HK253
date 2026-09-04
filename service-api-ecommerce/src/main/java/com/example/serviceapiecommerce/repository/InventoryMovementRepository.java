package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.InventoryMovement;
import com.example.serviceapiecommerce.entity.InventoryMovementType;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InventoryMovementRepository extends JpaRepository<InventoryMovement, Long> {
    Optional<InventoryMovement> findByIdempotencyKey(String idempotencyKey);

    List<InventoryMovement> findByProductVariant_IdOrderByCreatedAtDescIdDesc(Long productVariantId);

    List<InventoryMovement> findByOrder_IdOrderByCreatedAtDescIdDesc(Long orderId);

    List<InventoryMovement> findByReservation_IdOrderByCreatedAtDescIdDesc(Long reservationId);

    List<InventoryMovement> findByMovementTypeOrderByCreatedAtDescIdDesc(InventoryMovementType movementType);
}
