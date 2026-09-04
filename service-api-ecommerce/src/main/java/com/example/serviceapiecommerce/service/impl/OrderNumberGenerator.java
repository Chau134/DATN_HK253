package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.repository.OrderRepository;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import org.springframework.stereotype.Component;

@Component
public class OrderNumberGenerator {
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter
            .ofPattern("yyyyMMddHHmmss")
            .withZone(ZoneOffset.UTC);
    private static final String ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ";

    private final SecureRandom random = new SecureRandom();
    private final OrderRepository orderRepository;

    public OrderNumberGenerator(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public String nextOrderNumber() {
        for (int attempt = 0; attempt < 10; attempt++) {
            String orderNumber = "ORD-" + FORMATTER.format(Instant.now()) + "-" + randomSuffix();
            if (!orderRepository.existsByOrderNumber(orderNumber)) {
                return orderNumber;
            }
        }
        throw new IllegalStateException("order_number_generation_failed");
    }

    private String randomSuffix() {
        StringBuilder suffix = new StringBuilder(8);
        for (int i = 0; i < 8; i++) {
            suffix.append(ALPHABET.charAt(random.nextInt(ALPHABET.length())));
        }
        return suffix.toString();
    }
}
