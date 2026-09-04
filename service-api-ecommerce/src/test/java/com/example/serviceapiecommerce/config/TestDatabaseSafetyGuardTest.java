package com.example.serviceapiecommerce.config;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class TestDatabaseSafetyGuardTest {

    @Test
    void rejectsTheOperationalDacnSchema() {
        assertThatThrownBy(() -> TestDatabaseSafetyGuard.validateJdbcUrl(
                "jdbc:mysql://localhost:3306/DACN?useSSL=false"
        ))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Refusing to run integration tests")
                .hasMessageContaining("DACN");
    }

    @Test
    void rejectsAnySchemaThatIsNotExplicitlyNamedForTesting() {
        assertThatThrownBy(() -> TestDatabaseSafetyGuard.validateJdbcUrl(
                "jdbc:mysql://localhost:3306/DACN_staging?useSSL=false"
        ))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("DACN_staging");
    }

    @Test
    void acceptsAnExplicitIsolatedTestSchema() {
        assertThatCode(() -> TestDatabaseSafetyGuard.validateJdbcUrl(
                "jdbc:mysql://localhost:3306/DACN_codex_test_20260829?useSSL=false"
        )).doesNotThrowAnyException();
    }
}
