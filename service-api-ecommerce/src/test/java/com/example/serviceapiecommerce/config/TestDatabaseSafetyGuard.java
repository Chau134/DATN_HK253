package com.example.serviceapiecommerce.config;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.beans.BeansException;
import org.springframework.beans.factory.config.BeanFactoryPostProcessor;
import org.springframework.beans.factory.config.ConfigurableListableBeanFactory;
import org.springframework.context.EnvironmentAware;
import org.springframework.core.Ordered;
import org.springframework.core.PriorityOrdered;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@Component
public final class TestDatabaseSafetyGuard
        implements BeanFactoryPostProcessor, EnvironmentAware, PriorityOrdered {

    private static final Pattern MYSQL_SCHEMA = Pattern.compile(
            "^jdbc:mysql://[^/]+/([^?;]+)",
            Pattern.CASE_INSENSITIVE
    );

    private Environment environment;

    @Override
    public void setEnvironment(Environment environment) {
        this.environment = environment;
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }

    @Override
    public void postProcessBeanFactory(ConfigurableListableBeanFactory beanFactory) throws BeansException {
        validateJdbcUrl(environment == null ? "" : environment.getProperty("spring.datasource.url", ""));
    }

    static void validateJdbcUrl(String jdbcUrl) {
        Matcher matcher = MYSQL_SCHEMA.matcher(jdbcUrl == null ? "" : jdbcUrl.trim());
        if (!matcher.find()) {
            throw new IllegalStateException(
                    "Integration tests require an explicit MySQL test schema via TEST_SPRING_DATASOURCE_URL"
            );
        }

        String schema = matcher.group(1).toLowerCase(Locale.ROOT);
        if (schema.equals("dacn") || !schema.contains("test")) {
            throw new IllegalStateException(
                    "Refusing to run integration tests on non-test schema '" + matcher.group(1) + "'"
            );
        }
    }
}
