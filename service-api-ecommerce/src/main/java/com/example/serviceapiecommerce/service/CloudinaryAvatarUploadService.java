package com.example.serviceapiecommerce.service;

import org.springframework.web.multipart.MultipartFile;

public interface CloudinaryAvatarUploadService {
    String uploadAvatar(Long userAccountId, MultipartFile file);

    String uploadProductImage(Long productId, MultipartFile file);

    String uploadBlogImage(MultipartFile file);
}
