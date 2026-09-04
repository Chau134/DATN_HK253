package com.example.serviceapiecommerce.dto.cart;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record CartItemResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("product_id")
        Long productId,

        @JsonProperty("product_variant_id")
        Long productVariantId,

        @JsonProperty("sku_id")
        Long skuId,

        @JsonProperty("title")
        String title,

        @JsonProperty("title_vi")
        String titleVi,

        @JsonProperty("brand")
        String brand,

        @JsonProperty("option_name")
        String optionName,

        @JsonProperty("option_value")
        String optionValue,

        @JsonProperty("unified_size")
        String unifiedSize,

        @JsonProperty("quantity")
        Integer quantity,

        @JsonProperty("selected")
        Boolean selected,

        @JsonProperty("inventory_count")
        Integer inventoryCount,

        @JsonProperty("available")
        Boolean available,

        @JsonProperty("unit_price")
        BigDecimal unitPrice,

        @JsonProperty("discounted_price")
        BigDecimal discountedPrice,

        @JsonProperty("effective_price")
        BigDecimal effectivePrice,

        @JsonProperty("line_subtotal")
        BigDecimal lineSubtotal,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("image_url")
        String imageUrl
) {
}
