package com.example.serviceapiecommerce.service;

import com.example.serviceapiecommerce.dto.ai.AiProductResultDto;
import com.example.serviceapiecommerce.dto.response.ProductCardResponse;
import java.util.List;

public interface AiProductResolver {
    List<ProductCardResponse> resolve(List<AiProductResultDto> rankedResults);
}
