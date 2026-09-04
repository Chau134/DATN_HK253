package com.example.serviceapiecommerce.entity;

public enum PaymentTransactionType {
    AUTHORIZE,
    CAPTURE,
    SALE,
    REFUND,
    VOID,
    CANCEL,
    COD_CONFIRM,
    WEBHOOK_SYNC
}
