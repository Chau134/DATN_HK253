package com.example.serviceapiecommerce.repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class AiSyncStateRepository {
    private static final String CREATE_TABLE_SQL = """
            create table if not exists ai_sync_state (
                id bigint not null auto_increment,
                sync_name varchar(100) not null,
                last_success_at timestamp(6) null,
                updated_at timestamp(6) not null default current_timestamp(6),
                primary key (id),
                unique key uk_ai_sync_state_sync_name (sync_name)
            )
            """;

    private final JdbcTemplate jdbcTemplate;

    public AiSyncStateRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<Instant> findLastSuccessAt(String syncName) {
        ensureTable();
        List<Timestamp> timestamps = jdbcTemplate.query(
                """
                        select last_success_at
                        from ai_sync_state
                        where sync_name = ?
                        """,
                (rs, rowNum) -> rs.getTimestamp("last_success_at"),
                syncName
        );
        if (timestamps.isEmpty() || timestamps.getFirst() == null) {
            return Optional.empty();
        }
        return Optional.of(timestamps.getFirst().toInstant());
    }

    public void markSuccessfulSync(String syncName, Instant lastSuccessAt) {
        ensureTable();
        Instant now = Instant.now();
        jdbcTemplate.update(
                """
                        insert into ai_sync_state (sync_name, last_success_at, updated_at)
                        values (?, ?, ?)
                        on duplicate key update
                            last_success_at = values(last_success_at),
                            updated_at = values(updated_at)
                        """,
                syncName,
                Timestamp.from(lastSuccessAt),
                Timestamp.from(now)
        );
    }

    private void ensureTable() {
        jdbcTemplate.execute(CREATE_TABLE_SQL);
    }
}
