package com.example.serviceapiecommerce.repository;

import com.example.serviceapiecommerce.entity.ChatMessageProduct;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatMessageProductRepository extends JpaRepository<ChatMessageProduct, Long> {
}
