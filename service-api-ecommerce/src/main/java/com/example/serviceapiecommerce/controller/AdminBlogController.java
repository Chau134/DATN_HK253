package com.example.serviceapiecommerce.controller;

import com.example.serviceapiecommerce.dto.blog.BlogDetailResponse;
import com.example.serviceapiecommerce.dto.blog.BlogRequest;
import com.example.serviceapiecommerce.dto.blog.BlogSummaryResponse;
import com.example.serviceapiecommerce.entity.BlogCategory;
import com.example.serviceapiecommerce.entity.BlogStatus;
import com.example.serviceapiecommerce.security.AuthenticatedUser;
import com.example.serviceapiecommerce.service.BlogService;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/admin/blogs")
public class AdminBlogController {
    private final BlogService blogService;

    public AdminBlogController(BlogService blogService) {
        this.blogService = blogService;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public BlogDetailResponse createBlog(
            @AuthenticationPrincipal AuthenticatedUser currentUser,
            @RequestParam("title") String title,
            @RequestParam(value = "summary", required = false) String summary,
            @RequestParam(value = "content", required = false) String content,
            @RequestParam("category") BlogCategory category,
            @RequestParam("status") BlogStatus status,
            @RequestParam(value = "published_at", required = false) String publishedAtStr,
            @RequestPart(value = "file", required = false) MultipartFile file
    ) {
        Instant publishedAt = null;
        if (publishedAtStr != null && !publishedAtStr.isBlank()) {
            publishedAt = Instant.parse(publishedAtStr);
        }
        BlogRequest request = new BlogRequest(title, summary, content, category, status, publishedAt);
        return blogService.createBlog(request, currentUser.id(), file);
    }

    @GetMapping
    public List<BlogSummaryResponse> getAllBlogs() {
        return blogService.getAllBlogs();
    }

    @GetMapping("/{id}")
    public BlogDetailResponse getBlogById(@PathVariable Long id) {
        return blogService.getBlogById(id);
    }

    @PutMapping(value = "/{id}", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BlogDetailResponse updateBlog(
            @PathVariable Long id,
            @RequestParam("title") String title,
            @RequestParam(value = "summary", required = false) String summary,
            @RequestParam(value = "content", required = false) String content,
            @RequestParam("category") BlogCategory category,
            @RequestParam("status") BlogStatus status,
            @RequestParam(value = "published_at", required = false) String publishedAtStr,
            @RequestPart(value = "file", required = false) MultipartFile file
    ) {
        Instant publishedAt = null;
        if (publishedAtStr != null && !publishedAtStr.isBlank()) {
            publishedAt = Instant.parse(publishedAtStr);
        }
        BlogRequest request = new BlogRequest(title, summary, content, category, status, publishedAt);
        return blogService.updateBlog(id, request, file);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteBlog(@PathVariable Long id) {
        blogService.deleteBlog(id);
    }
}
