package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.inventory.InventoryAdjustmentRequest;
import com.example.serviceapiecommerce.dto.inventory.InventoryMovementResponse;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.InventoryService;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/inventory")
public class AdminInventoryController {
    private final InventoryService inventoryService;

    public AdminInventoryController(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    @PostMapping("/variants/{productVariantId}/adjustments")
    public InventoryMovementResponse adjustVariantStock(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @PathVariable Long productVariantId,
            @Valid @RequestBody InventoryAdjustmentRequest request
    ) {
        return inventoryService.adjustVariantStock(productVariantId, currentUser.id(), request);
    }
}
