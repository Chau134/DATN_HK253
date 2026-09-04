package com.example.serviceapiecommerce.service.impl;

import com.example.serviceapiecommerce.dto.ai.AiChatFeedbackRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatResponse;
import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.response.AiChatFeedbackResponse;
import com.example.serviceapiecommerce.dto.response.ProductCardResponse;
import com.example.serviceapiecommerce.entity.ChatFeedback;
import com.example.serviceapiecommerce.entity.ChatMessage;
import com.example.serviceapiecommerce.entity.ChatMessageProduct;
import com.example.serviceapiecommerce.entity.ChatSession;
import com.example.serviceapiecommerce.entity.Product;
import com.example.serviceapiecommerce.entity.UserAccount;
import com.example.serviceapiecommerce.repository.ChatFeedbackRepository;
import com.example.serviceapiecommerce.repository.ChatMessageProductRepository;
import com.example.serviceapiecommerce.repository.ChatMessageRepository;
import com.example.serviceapiecommerce.repository.ChatSessionRepository;
import com.example.serviceapiecommerce.repository.ProductRepository;
import com.example.serviceapiecommerce.repository.UserAccountRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AiChatPersistenceService {
    private static final Logger log = LoggerFactory.getLogger(AiChatPersistenceService.class);
    private static final String WARNING_UNAVAILABLE = "ai_service_unavailable";

    private final ChatSessionRepository chatSessionRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final ChatMessageProductRepository chatMessageProductRepository;
    private final ChatFeedbackRepository chatFeedbackRepository;
    private final UserAccountRepository userAccountRepository;
    private final ProductRepository productRepository;
    private final ObjectMapper objectMapper;

    public AiChatPersistenceService(
            ChatSessionRepository chatSessionRepository,
            ChatMessageRepository chatMessageRepository,
            ChatMessageProductRepository chatMessageProductRepository,
            ChatFeedbackRepository chatFeedbackRepository,
            UserAccountRepository userAccountRepository,
            ProductRepository productRepository,
            ObjectMapper objectMapper
    ) {
        this.chatSessionRepository = chatSessionRepository;
        this.chatMessageRepository = chatMessageRepository;
        this.chatMessageProductRepository = chatMessageProductRepository;
        this.chatFeedbackRepository = chatFeedbackRepository;
        this.userAccountRepository = userAccountRepository;
        this.productRepository = productRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public Optional<Long> recordChatTurn(
            AiChatRequest request,
            AiChatResponse aiResponse,
            List<ProductCardResponse> productCards
    ) {
        try {
            UserAccount userAccount = resolveUser(request == null ? null : request.userId()).orElse(null);
            ChatSession session = upsertSession(request, aiResponse, userAccount);
            ChatMessage message = saveMessage(request, aiResponse, session, userAccount);
            saveMessageProducts(message, aiResponse.productIds(), productCards);
            return Optional.of(message.getId());
        } catch (RuntimeException exception) {
            log.warn("ai_chat_history_save_failed session_id={}", request == null ? null : request.sessionId(), exception);
            return Optional.empty();
        }
    }

    @Transactional
    public AiChatFeedbackResponse saveFeedback(AiChatFeedbackRequest request) {
        ChatMessage message = chatMessageRepository.findById(request.chatMessageId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "chat_message_not_found"));
        requireFeedbackOwnership(message, request.userId());
        UserAccount userAccount = resolveUser(request.userId()).orElse(null);
        ChatFeedback feedback = chatFeedbackRepository.findByChatMessage_Id(request.chatMessageId())
                .orElseGet(ChatFeedback::new);
        feedback.setChatMessage(message);
        feedback.setUserAccount(userAccount);
        feedback.setExternalUserId(externalUserId(request.userId()));
        feedback.setRating(request.rating());
        feedback.setHelpful(request.helpful());
        feedback.setFeedbackType(truncate(request.feedbackType(), 50));
        feedback.setComment(request.comment());

        ChatFeedback saved = chatFeedbackRepository.save(feedback);
        return new AiChatFeedbackResponse(
                saved.getId(),
                saved.getChatMessage().getId(),
                saved.getRating(),
                saved.getHelpful(),
                saved.getFeedbackType(),
                saved.getComment()
        );
    }

    private void requireFeedbackOwnership(ChatMessage message, String userId) {
        if (message.getUserAccount() != null) {
            Long requestedAccountId = parseLong(userId);
            if (!message.getUserAccount().getId().equals(requestedAccountId)) {
                throw new ResponseStatusException(HttpStatus.FORBIDDEN, "chat_feedback_forbidden");
            }
            return;
        }
        if (message.getExternalUserId() == null || !message.getExternalUserId().equals(userId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "chat_feedback_forbidden");
        }
    }

    private ChatSession upsertSession(AiChatRequest request, AiChatResponse aiResponse, UserAccount userAccount) {
        String sessionKey = sessionKey(request, aiResponse);
        ChatSession session = chatSessionRepository.findBySessionKey(sessionKey).orElseGet(ChatSession::new);
        session.setSessionKey(sessionKey);
        session.setUserAccount(userAccount);
        session.setExternalUserId(externalUserId(request == null ? null : request.userId()));
        session.setLocale(locale(request));
        session.setStatus("ACTIVE");
        session.setLastMessageAt(Instant.now());
        return chatSessionRepository.save(session);
    }

    private ChatMessage saveMessage(
            AiChatRequest request,
            AiChatResponse aiResponse,
            ChatSession session,
            UserAccount userAccount
    ) {
        ChatMessage message = new ChatMessage();
        message.setChatSession(session);
        message.setUserAccount(userAccount);
        message.setExternalUserId(externalUserId(request == null ? null : request.userId()));
        message.setUserMessage(request == null ? null : request.message());
        message.setAssistantMessage(aiResponse.message());
        message.setImagePresent(request != null && request.image() != null);
        message.setImageMetadata(imageMetadataJson(request));
        message.setFiltersJson(json(aiResponse.filters()));
        message.setRewrittenQuery(truncate(aiResponse.rewrittenQuery(), 1000));
        message.setWarningsJson(json(aiResponse.warnings()));
        message.setStatus(aiResponse.warnings().contains(WARNING_UNAVAILABLE) ? "UNAVAILABLE" : "SUCCESS");
        return chatMessageRepository.save(message);
    }

    private void saveMessageProducts(
            ChatMessage message,
            List<AiProductResultDto> rankedResults,
            List<ProductCardResponse> productCards
    ) {
        Map<String, ProductCardResponse> cardsByProductId = new LinkedHashMap<>();
        for (ProductCardResponse card : productCards) {
            cardsByProductId.put(card.productId(), card);
        }
        LinkedHashSet<Long> productIds = new LinkedHashSet<>();
        for (AiProductResultDto result : rankedResults) {
            Long productId = parseLong(result.productId());
            if (productId != null) {
                productIds.add(productId);
            }
        }
        Map<Long, Product> productsById = new LinkedHashMap<>();
        for (Product product : productRepository.findAllById(productIds)) {
            productsById.put(product.getId(), product);
        }

        List<ChatMessageProduct> items = new ArrayList<>();
        int rank = 1;
        for (AiProductResultDto result : rankedResults) {
            if (result.productId() == null || result.productId().isBlank()) {
                continue;
            }
            ChatMessageProduct item = new ChatMessageProduct();
            item.setChatMessage(message);
            item.setAiProductId(truncate(result.productId(), 120));
            item.setProduct(productsById.get(parseLong(result.productId())));
            item.setRankPosition(rank++);
            item.setScore(result.score() == null ? null : BigDecimal.valueOf(result.score()));
            item.setSource(truncate(result.source(), 50));
            item.setProductSnapshotJson(json(cardsByProductId.get(result.productId())));
            items.add(item);
        }
        if (!items.isEmpty()) {
            chatMessageProductRepository.saveAll(items);
        }
    }

    private Optional<UserAccount> resolveUser(String userId) {
        Long id = parseLong(userId);
        if (id == null) {
            return Optional.empty();
        }
        return userAccountRepository.findById(id);
    }

    private String imageMetadataJson(AiChatRequest request) {
        if (request == null || request.image() == null) {
            return null;
        }
        Map<String, Object> metadata = new LinkedHashMap<>();
        Map<String, Object> image = new LinkedHashMap<>(request.image());
        image.computeIfPresent("data_base64", (ignoredKey, ignoredValue) -> "[redacted]");
        image.computeIfPresent("data", (ignoredKey, ignoredValue) -> "[redacted]");
        metadata.put("image", image);
        metadata.put("crop_box", request.cropBox());
        return json(metadata);
    }

    private String json(Object value) {
        if (value == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            log.warn("ai_chat_json_serialization_failed type={}", value.getClass().getName(), exception);
            return null;
        }
    }

    private String sessionKey(AiChatRequest request, AiChatResponse aiResponse) {
        String responseSessionId = aiResponse == null ? null : aiResponse.sessionId();
        if (responseSessionId != null && !responseSessionId.isBlank()) {
            return truncate(responseSessionId, 120);
        }
        String requestSessionId = request == null ? null : request.sessionId();
        if (requestSessionId != null && !requestSessionId.isBlank()) {
            return truncate(requestSessionId, 120);
        }
        return "generated-" + UUID.randomUUID();
    }

    private String locale(AiChatRequest request) {
        if (request == null || request.locale() == null || request.locale().isBlank()) {
            return "vi-VN";
        }
        return truncate(request.locale(), 20);
    }

    private String externalUserId(String userId) {
        if (userId == null || userId.isBlank()) {
            return null;
        }
        return truncate(userId, 120);
    }

    private Long parseLong(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private String truncate(String value, int maxLength) {
        if (value == null || value.length() <= maxLength) {
            return value;
        }
        return value.substring(0, maxLength);
    }
}
