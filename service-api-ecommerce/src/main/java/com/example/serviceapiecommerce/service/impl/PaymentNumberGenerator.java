package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.repository.PaymentRepository;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import org.springframework.stereotype.Component;

@Component
public class PaymentNumberGenerator {
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter
            .ofPattern("yyyyMMddHHmmss")
            .withZone(ZoneOffset.UTC);
    private static final String ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ";

    private final SecureRandom random = new SecureRandom();
    private final PaymentRepository paymentRepository;

    public PaymentNumberGenerator(PaymentRepository paymentRepository) {
        this.paymentRepository = paymentRepository;
    }

    public String nextPaymentNumber() {
        for (int attempt = 0; attempt < 10; attempt++) {
            String paymentNumber = "PAY-" + FORMATTER.format(Instant.now()) + "-" + randomSuffix();
            if (!paymentRepository.existsByPaymentNumber(paymentNumber)) {
                return paymentNumber;
            }
        }
        throw new IllegalStateException("payment_number_generation_failed");
    }

    private String randomSuffix() {
        StringBuilder suffix = new StringBuilder(8);
        for (int i = 0; i < 8; i++) {
            suffix.append(ALPHABET.charAt(random.nextInt(ALPHABET.length())));
        }
        return suffix.toString();
    }
}
