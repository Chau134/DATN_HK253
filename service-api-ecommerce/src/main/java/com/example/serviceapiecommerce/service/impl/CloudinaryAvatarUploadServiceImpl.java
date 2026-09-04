package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.config.CloudinaryProperties;
import com.example.serviceapiecommerce.service.CloudinaryAvatarUploadService;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.multipart.MultipartFile;

@Service
public class CloudinaryAvatarUploadServiceImpl implements CloudinaryAvatarUploadService {
    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            MediaType.IMAGE_JPEG_VALUE,
            MediaType.IMAGE_PNG_VALUE,
            "image/webp",
            "image/gif",
            "image/bmp"
    );

    private final CloudinaryProperties properties;
    private final RestClient restClient;

    public CloudinaryAvatarUploadServiceImpl(CloudinaryProperties properties, RestClient.Builder restClientBuilder) {
        this.properties = properties;
        this.restClient = restClientBuilder.build();
    }

    @Override
    public String uploadAvatar(Long userAccountId, MultipartFile file) {
        validate(file, properties.resolvedMaxAvatarBytes(), "avatar");

        Map<String, String> params = new LinkedHashMap<>();
        params.put("timestamp", String.valueOf(Instant.now().getEpochSecond()));
        params.put("folder", properties.resolvedAvatarFolder());
        params.put("public_id", "user-" + userAccountId);
        params.put("overwrite", "true");

        return upload(file, params);
    }

    @Override
    public String uploadProductImage(Long productId, MultipartFile file) {
        validate(file, properties.resolvedMaxProductImageBytes(), "product_image");

        Map<String, String> params = new LinkedHashMap<>();
        params.put("timestamp", String.valueOf(Instant.now().getEpochSecond()));
        params.put("folder", properties.resolvedProductFolder() + "/" + productId);

        return upload(file, params);
    }

    @Override
    public String uploadBlogImage(MultipartFile file) {
        validate(file, properties.resolvedMaxProductImageBytes(), "blog_image");

        Map<String, String> params = new LinkedHashMap<>();
        params.put("timestamp", String.valueOf(Instant.now().getEpochSecond()));
        params.put("folder", properties.resolvedProductFolder() + "/blogs");

        return upload(file, params);
    }

    private String upload(MultipartFile file, Map<String, String> params) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("api_key", properties.apiKey());
        params.forEach(body::add);
        body.add("signature", signature(params));
        body.add("file", fileResource(file));

        Map<String, Object> response;
        try {
            response = restClient.post()
                    .uri("https://api.cloudinary.com/v1_1/{cloudName}/image/upload", properties.cloudName())
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .body(new ParameterizedTypeReference<>() {
                    });
        } catch (RestClientResponseException exception) {
            String status = String.valueOf(exception.getStatusCode().value());
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "cloudinary_upload_failed_" + status, exception);
        }

        Object secureUrl = response == null ? null : response.get("secure_url");
        if (!(secureUrl instanceof String url) || url.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "cloudinary_upload_failed");
        }
        return url;
    }

    private void validate(MultipartFile file, long maxBytes, String errorPrefix) {
        if (!properties.configured()) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "cloudinary_not_configured");
        }
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, errorPrefix + "_file_required");
        }
        if (file.getSize() > maxBytes) {
            throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, errorPrefix + "_file_too_large");
        }
        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_CONTENT_TYPES.contains(contentType.toLowerCase())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, errorPrefix + "_file_type_not_supported");
        }
    }

    private ByteArrayResource fileResource(MultipartFile file) {
        try {
            byte[] bytes = file.getBytes();
            String filename = file.getOriginalFilename() == null ? "avatar" : file.getOriginalFilename();
            return new ByteArrayResource(bytes) {
                @Override
                public String getFilename() {
                    return filename;
                }
            };
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "avatar_file_read_failed", exception);
        }
    }

    private String signature(Map<String, String> params) {
        String payload = params.entrySet().stream()
                .sorted(Comparator.comparing(Map.Entry::getKey))
                .map(entry -> entry.getKey() + "=" + entry.getValue())
                .collect(Collectors.joining("&"))
                + properties.apiSecret();
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-1");
            byte[] bytes = digest.digest(payload.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder(bytes.length * 2);
            for (byte item : bytes) {
                result.append(String.format("%02x", item));
            }
            return result.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-1 digest is not available", exception);
        }
    }
}
