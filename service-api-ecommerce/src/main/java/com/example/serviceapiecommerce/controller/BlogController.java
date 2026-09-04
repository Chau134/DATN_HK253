package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.blog.BlogDetailResponse;
import com.example.serviceapiecommerce.dto.blog.BlogSummaryResponse;
import com.example.serviceapiecommerce.service.BlogService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;

@RestController
@RequestMapping("/api/blogs")
public class BlogController {
    private final BlogService blogService;

    public BlogController(BlogService blogService) {
        this.blogService = blogService;
    }

    @GetMapping
    public List<BlogSummaryResponse> getPublishedBlogs() {
        return blogService.getPublishedBlogs();
    }

    @GetMapping("/slug/{slug}")
    public BlogDetailResponse getBlogBySlug(@PathVariable String slug) {
        return blogService.getBlogBySlug(slug);
    }
}
