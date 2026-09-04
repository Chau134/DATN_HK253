package com.example.serviceapiecommerce.observability;

import org.springframework.boot.restclient.RestClientCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class CorrelationIdRestClientConfiguration {
    @Bean
    RestClientCustomizer correlationIdRestClientCustomizer() {
        return builder -> builder.requestInterceptor((request, body, execution) -> {
            request.getHeaders().set(CorrelationId.HEADER_NAME, CorrelationId.currentOrCreate());
            return execution.execute(request, body);
        });
    }
}
