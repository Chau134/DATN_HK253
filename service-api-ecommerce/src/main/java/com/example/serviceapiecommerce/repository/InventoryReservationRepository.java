package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.InventoryReservation;
import com.example.serviceapiecommerce.entity.InventoryReservationStatus;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InventoryReservationRepository extends JpaRepository<InventoryReservation, Long> {
    Optional<InventoryReservation> findByReservationKey(String reservationKey);

    List<InventoryReservation> findByOrder_IdOrderByCreatedAtDescIdDesc(Long orderId);

    List<InventoryReservation> findByOrder_IdAndStatusOrderByCreatedAtAscIdAsc(
            Long orderId,
            InventoryReservationStatus status
    );

    List<InventoryReservation> findByOrder_IdAndStatusInOrderByCreatedAtAscIdAsc(
            Long orderId,
            Collection<InventoryReservationStatus> statuses
    );

    List<InventoryReservation> findByCart_IdOrderByCreatedAtDescIdDesc(Long cartId);

    List<InventoryReservation> findByProductVariant_IdAndStatusOrderByCreatedAtAscIdAsc(
            Long productVariantId,
            InventoryReservationStatus status
    );

    List<InventoryReservation> findByStatusAndExpiresAtBeforeOrderByExpiresAtAscIdAsc(
            InventoryReservationStatus status,
            Instant expiresAt
    );

    @Query("""
            select coalesce(sum(reservation.quantity), 0)
            from InventoryReservation reservation
            where reservation.productVariant.id = :productVariantId
              and reservation.status = :status
            """)
    Long sumQuantityByProductVariantIdAndStatus(
            @Param("productVariantId") Long productVariantId,
            @Param("status") InventoryReservationStatus status
    );
}
