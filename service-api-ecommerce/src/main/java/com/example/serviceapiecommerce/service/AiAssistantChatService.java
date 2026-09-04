package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.ai.AiChatFeedbackRequest;
import com.example.serviceapiecommerce.dto.ai.AiChatRequest;
import com.example.serviceapiecommerce.dto.response.AiChatFeedbackResponse;
import com.example.serviceapiecommerce.dto.response.AiAssistantChatResponse;

public interface AiAssistantChatService {
    AiAssistantChatResponse chat(AiChatRequest request);

    AiChatFeedbackResponse saveFeedback(AiChatFeedbackRequest request);
}
