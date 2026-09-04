package com.example.serviceapiecommerce.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.cloudinary")
public record CloudinaryProperties(
        String cloudName,
        String apiKey,
        String apiSecret,
        String avatarFolder,
        long maxAvatarBytes,
        String productFolder,
        long maxProductImageBytes
) {
    public String resolvedAvatarFolder() {
        return isBlank(avatarFolder) ? "dacn/avatar" : avatarFolder.trim();
    }

    public long resolvedMaxAvatarBytes() {
        return maxAvatarBytes <= 0 ? 5 * 1024 * 1024 : maxAvatarBytes;
    }

    public String resolvedProductFolder() {
        return isBlank(productFolder) ? "dacn/products" : productFolder.trim();
    }

    public long resolvedMaxProductImageBytes() {
        return maxProductImageBytes <= 0 ? 8 * 1024 * 1024 : maxProductImageBytes;
    }

    public boolean configured() {
        return !isBlank(cloudName) && !isBlank(apiKey) && !isBlank(apiSecret);
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
