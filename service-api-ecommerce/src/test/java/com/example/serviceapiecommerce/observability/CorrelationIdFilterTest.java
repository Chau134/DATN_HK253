package com.example.serviceapiecommerce.observability;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

class CorrelationIdFilterTest {
    private final MockMvc mockMvc = MockMvcBuilders
            .standaloneSetup(new ProbeController())
            .addFilters(new CorrelationIdFilter())
            .build();

    @Test
    void preservesIncomingCorrelationIdAndClearsMdc() throws Exception {
        mockMvc.perform(get("/probe").header(CorrelationId.HEADER_NAME, "browser-request-42"))
                .andExpect(status().isOk())
                .andExpect(header().string(CorrelationId.HEADER_NAME, "browser-request-42"))
                .andExpect(header().string("X-Probe-Correlation-ID", "browser-request-42"));

        assertThat(MDC.get(CorrelationId.MDC_KEY)).isNull();
    }

    @Test
    void generatesCorrelationIdWhenHeaderIsMissing() throws Exception {
        String generated = mockMvc.perform(get("/probe"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getHeader(CorrelationId.HEADER_NAME);

        assertThat(generated).isNotBlank().matches("[A-Za-z0-9._-]{1,128}");
    }

    @RestController
    static class ProbeController {
        @GetMapping("/probe")
        ResponseEntity<Void> probe() {
            return ResponseEntity.ok()
                    .header("X-Probe-Correlation-ID", MDC.get(CorrelationId.MDC_KEY))
                    .build();
        }
    }
}
