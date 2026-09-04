package com.example.serviceapiecommerce.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "ai.service")
public record AiServiceProperties(
        boolean enabled,
        boolean mock,
        String baseUrl,
        String internalApiKey,
        int timeoutSeconds,
        Sync sync
) {
    public int batchSize() {
        return sync.batchSize();
    }

    public String cron() {
        return sync.cron();
    }

    public record Sync(
            int batchSize,
            String cron
    ) {
    }
}
