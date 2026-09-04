package com.example.serviceapiecommerce.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

class AiServicePropertiesTest {
    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
            .withUserConfiguration(TestConfig.class);

    @Test
    void bindsAiServiceProperties() {
        contextRunner
                .withPropertyValues(
                        "ai.service.enabled=true",
                        "ai.service.mock=false",
                        "ai.service.base-url=http://localhost:8000",
                        "ai.service.internal-api-key=test-key",
                        "ai.service.timeout-seconds=45",
                        "ai.service.sync.batch-size=75",
                        "ai.service.sync.cron=0 */5 * * * *"
                )
                .run(context -> {
                    AiServiceProperties properties = context.getBean(AiServiceProperties.class);

                    assertThat(properties.enabled()).isTrue();
                    assertThat(properties.mock()).isFalse();
                    assertThat(properties.baseUrl()).isEqualTo("http://localhost:8000");
                    assertThat(properties.internalApiKey()).isEqualTo("test-key");
                    assertThat(properties.timeoutSeconds()).isEqualTo(45);
                    assertThat(properties.sync().batchSize()).isEqualTo(75);
                    assertThat(properties.sync().cron()).isEqualTo("0 */5 * * * *");
                    assertThat(properties.batchSize()).isEqualTo(75);
                    assertThat(properties.cron()).isEqualTo("0 */5 * * * *");
                });
    }

    @Configuration
    @EnableConfigurationProperties(AiServiceProperties.class)
    static class TestConfig {
    }
}
