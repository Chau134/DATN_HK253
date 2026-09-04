package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.blog.BlogDetailResponse;
import com.example.serviceapiecommerce.dto.blog.BlogRequest;
import com.example.serviceapiecommerce.dto.blog.BlogSummaryResponse;
import org.springframework.web.multipart.MultipartFile;
import java.util.List;

public interface BlogService {
    List<BlogSummaryResponse> getAllBlogs();
    List<BlogSummaryResponse> getPublishedBlogs();
    BlogDetailResponse getBlogById(Long id);
    BlogDetailResponse getBlogBySlug(String slug);
    BlogDetailResponse createBlog(BlogRequest request, Long authorId, MultipartFile file);
    BlogDetailResponse updateBlog(Long id, BlogRequest request, MultipartFile file);
    void deleteBlog(Long id);
}
