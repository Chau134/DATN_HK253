package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.service.InventoryService;
import java.time.Instant;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class InventoryReservationExpiryJob {
    private final InventoryService inventoryService;

    public InventoryReservationExpiryJob(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    @Scheduled(fixedDelayString = "${app.inventory.reservation-expiry-fixed-delay-ms:60000}")
    public void expireReservations() {
        inventoryService.expireActiveReservations(Instant.now());
    }
}
