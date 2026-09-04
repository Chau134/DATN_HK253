package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.blog.BlogDetailResponse;
import com.example.serviceapiecommerce.dto.blog.BlogRequest;
import com.example.serviceapiecommerce.dto.blog.BlogSummaryResponse;
import com.example.serviceapiecommerce.entity.Blog;
import com.example.serviceapiecommerce.entity.BlogStatus;
import com.example.serviceapiecommerce.repository.BlogRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.example.serviceapiecommerce.service.BlogService;
import com.example.serviceapiecommerce.service.CloudinaryAvatarUploadService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.multipart.MultipartFile;
import java.time.Instant;
import java.util.List;

@Service
public class BlogServiceImpl implements BlogService {
    private final BlogRepository blogRepository;
    private final UserAccountRepository userAccountRepository;
    private final CloudinaryAvatarUploadService cloudinaryAvatarUploadService;

    public BlogServiceImpl(
            BlogRepository blogRepository,
            UserAccountRepository userAccountRepository,
            CloudinaryAvatarUploadService cloudinaryAvatarUploadService
    ) {
        this.blogRepository = blogRepository;
        this.userAccountRepository = userAccountRepository;
        this.cloudinaryAvatarUploadService = cloudinaryAvatarUploadService;
    }

    @Override
    @Transactional(readOnly = true)
    public List<BlogSummaryResponse> getAllBlogs() {
        return blogRepository.findAllByOrderByCreatedAtDescIdDesc().stream()
                .map(this::toSummaryResponse)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public List<BlogSummaryResponse> getPublishedBlogs() {
        return blogRepository.findPublishedBlogs(Instant.now()).stream()
                .map(this::toSummaryResponse)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public BlogDetailResponse getBlogById(Long id) {
        return blogRepository.findById(id)
                .map(this::toDetailResponse)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "blog_not_found"));
    }

    @Override
    @Transactional(readOnly = true)
    public BlogDetailResponse getBlogBySlug(String slug) {
        return blogRepository.findBySlug(slug)
                .map(this::toDetailResponse)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "blog_not_found"));
    }

    @Override
    @Transactional
    public BlogDetailResponse createBlog(BlogRequest request, Long authorId, MultipartFile file) {
        Instant now = Instant.now();
        Blog blog = new Blog();
        blog.setTitle(request.title());
        blog.setSlug(generateUniqueSlug(request.title()));
        blog.setSummary(request.summary());
        blog.setContent(request.content());
        blog.setCategory(request.category());
        blog.setStatus(request.status());
        blog.setCreatedAt(now);
        blog.setUpdatedAt(now);

        if (authorId != null) {
            blog.setAuthor(userAccountRepository.getReferenceById(authorId));
        }

        // Set published date
        if (request.status() == BlogStatus.PUBLISHED) {
            blog.setPublishedAt(request.publishedAt() != null ? request.publishedAt() : now);
        } else {
            blog.setPublishedAt(request.publishedAt());
        }

        if (file != null && !file.isEmpty()) {
            String imgUrl = cloudinaryAvatarUploadService.uploadBlogImage(file);
            blog.setThumbnailUrl(imgUrl);
        }

        Blog saved = blogRepository.save(blog);
        return toDetailResponse(saved);
    }

    @Override
    @Transactional
    public BlogDetailResponse updateBlog(Long id, BlogRequest request, MultipartFile file) {
        Blog blog = blogRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "blog_not_found"));

        // If title changed, update slug
        if (!blog.getTitle().equalsIgnoreCase(request.title())) {
            blog.setSlug(generateUniqueSlug(request.title()));
        }
        blog.setTitle(request.title());
        blog.setSummary(request.summary());
        blog.setContent(request.content());
        blog.setCategory(request.category());
        blog.setStatus(request.status());
        blog.setUpdatedAt(Instant.now());

        // Set published date
        if (request.status() == BlogStatus.PUBLISHED) {
            if (blog.getPublishedAt() == null) {
                blog.setPublishedAt(request.publishedAt() != null ? request.publishedAt() : Instant.now());
            } else if (request.publishedAt() != null) {
                blog.setPublishedAt(request.publishedAt());
            }
        } else {
            blog.setPublishedAt(request.publishedAt());
        }

        if (file != null && !file.isEmpty()) {
            String imgUrl = cloudinaryAvatarUploadService.uploadBlogImage(file);
            blog.setThumbnailUrl(imgUrl);
        }

        Blog saved = blogRepository.save(blog);
        return toDetailResponse(saved);
    }

    @Override
    @Transactional
    public void deleteBlog(Long id) {
        Blog blog = blogRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "blog_not_found"));
        blogRepository.delete(blog);
    }

    private BlogSummaryResponse toSummaryResponse(Blog blog) {
        String authorName = blog.getAuthor() != null ? blog.getAuthor().getDisplayName() : "Ẩn danh";
        if (authorName == null && blog.getAuthor() != null) {
            authorName = blog.getAuthor().getFullName();
        }
        return new BlogSummaryResponse(
                blog.getId(),
                blog.getTitle(),
                blog.getSlug(),
                blog.getSummary(),
                blog.getThumbnailUrl(),
                blog.getCategory(),
                blog.getStatus(),
                authorName,
                blog.getPublishedAt(),
                blog.getCreatedAt()
        );
    }

    private BlogDetailResponse toDetailResponse(Blog blog) {
        String authorName = blog.getAuthor() != null ? blog.getAuthor().getDisplayName() : "Ẩn danh";
        if (authorName == null && blog.getAuthor() != null) {
            authorName = blog.getAuthor().getFullName();
        }
        return new BlogDetailResponse(
                blog.getId(),
                blog.getTitle(),
                blog.getSlug(),
                blog.getSummary(),
                blog.getContent(),
                blog.getThumbnailUrl(),
                blog.getCategory(),
                blog.getStatus(),
                authorName,
                blog.getPublishedAt(),
                blog.getCreatedAt(),
                blog.getUpdatedAt()
        );
    }

    private String generateUniqueSlug(String title) {
        String baseSlug = toSlug(title);
        if (baseSlug.isEmpty()) {
            baseSlug = "post-" + System.currentTimeMillis();
        }
        String slug = baseSlug;
        int count = 1;
        while (blogRepository.findBySlug(slug).isPresent()) {
            slug = baseSlug + "-" + count;
            count++;
        }
        return slug;
    }

    private static String toSlug(String input) {
        if (input == null || input.isBlank()) return "";
        String normalized = java.text.Normalizer.normalize(input, java.text.Normalizer.Form.NFD);
        String slug = normalized.replaceAll("\\p{InCombiningDiacriticalMarks}+", "");
        slug = slug.toLowerCase()
                   .replaceAll("[^a-z0-9\\s-]", "")
                   .replaceAll("\\s+", "-")
                   .replaceAll("-+", "-")
                   .trim();
        if (slug.startsWith("-")) slug = slug.substring(1);
        if (slug.endsWith("-")) slug = slug.substring(0, slug.length() - 1);
        return slug;
    }
}
