package com.example.serviceapiecommerce.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

class ApiExceptionHandlerTest {
    private final MockMvc mockMvc = MockMvcBuilders
            .standaloneSetup(new OversizeUploadController())
            .setControllerAdvice(new ApiExceptionHandler())
            .build();

    @Test
    void mapsOversizeUploadToPayloadTooLargeInsteadOfInternalServerError() throws Exception {
        mockMvc.perform(post("/test/upload-too-large"))
                .andExpect(status().isPayloadTooLarge())
                .andExpect(jsonPath("$.error").value("payload_too_large"))
                .andExpect(jsonPath("$.status").value(413))
                .andExpect(jsonPath("$.path").value("/test/upload-too-large"));
    }

    @RestController
    private static class OversizeUploadController {
        @PostMapping("/test/upload-too-large")
        void upload() {
            throw new MaxUploadSizeExceededException(5 * 1024 * 1024L);
        }
    }
}
