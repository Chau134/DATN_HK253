package com.example.serviceapiecommerce.dto.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record OrderItemResponse(
        @JsonProperty("id")
        Long id,

        @JsonProperty("source_product_id")
        Long sourceProductId,

        @JsonProperty("source_product_variant_id")
        Long sourceProductVariantId,

        @JsonProperty("sku_id")
        Long skuId,

        @JsonProperty("product_title")
        String productTitle,

        @JsonProperty("product_title_vi")
        String productTitleVi,

        @JsonProperty("brand_name")
        String brandName,

        @JsonProperty("variant_name")
        String variantName,

        @JsonProperty("option_name")
        String optionName,

        @JsonProperty("option_value")
        String optionValue,

        @JsonProperty("unified_size")
        String unifiedSize,

        @JsonProperty("image_url")
        String imageUrl,

        @JsonProperty("quantity")
        Integer quantity,

        @JsonProperty("unit_price")
        BigDecimal unitPrice,

        @JsonProperty("discounted_unit_price")
        BigDecimal discountedUnitPrice,

        @JsonProperty("effective_unit_price")
        BigDecimal effectiveUnitPrice,

        @JsonProperty("line_discount")
        BigDecimal lineDiscount,

        @JsonProperty("line_subtotal")
        BigDecimal lineSubtotal,

        @JsonProperty("line_total")
        BigDecimal lineTotal,

        @JsonProperty("currency")
        String currency,

        @JsonProperty("is_reviewed")
        Boolean isReviewed
) {
}
