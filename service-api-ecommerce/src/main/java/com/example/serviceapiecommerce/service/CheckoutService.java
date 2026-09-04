package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.order.CheckoutPreviewRequest;
import com.example.serviceapiecommerce.dto.order.CheckoutPreviewResponse;
import com.example.serviceapiecommerce.dto.order.CheckoutRequest;
import com.example.serviceapiecommerce.dto.order.OrderResponse;

public interface CheckoutService {
    OrderResponse checkout(Long userAccountId, CheckoutRequest request);
    CheckoutPreviewResponse preview(Long userAccountId, CheckoutPreviewRequest request);
}

