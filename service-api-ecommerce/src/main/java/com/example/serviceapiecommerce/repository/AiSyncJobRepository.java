package com.example.serviceapiecommerce.repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class AiSyncJobRepository {
    private static final String CREATE_TABLE_SQL = """
            create table if not exists ai_sync_job (
                job_id varchar(36) not null,
                sync_type varchar(50) not null,
                requested_limit int null,
                status varchar(20) not null,
                result_json longtext null,
                error_message varchar(255) null,
                created_at timestamp(6) not null,
                started_at timestamp(6) null,
                completed_at timestamp(6) null,
                updated_at timestamp(6) not null,
                primary key (job_id),
                key idx_ai_sync_job_status_created (status, created_at)
            )
            """;

    private final JdbcTemplate jdbcTemplate;

    public AiSyncJobRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        jdbcTemplate.execute(CREATE_TABLE_SQL);
        Instant now = Instant.now();
        jdbcTemplate.update(
                """
                        update ai_sync_job
                        set status = 'FAILED',
                            error_message = 'interrupted_by_application_restart',
                            completed_at = ?,
                            updated_at = ?
                        where status in ('QUEUED', 'RUNNING')
                        """,
                Timestamp.from(now),
                Timestamp.from(now)
        );
    }

    public void create(String jobId, String syncType, Integer requestedLimit) {
        Instant now = Instant.now();
        jdbcTemplate.update(
                """
                        insert into ai_sync_job (
                            job_id, sync_type, requested_limit, status, created_at, updated_at
                        ) values (?, ?, ?, 'QUEUED', ?, ?)
                        """,
                jobId,
                syncType,
                requestedLimit,
                Timestamp.from(now),
                Timestamp.from(now)
        );
    }

    public void markRunning(String jobId) {
        Instant now = Instant.now();
        jdbcTemplate.update(
                """
                        update ai_sync_job
                        set status = 'RUNNING', started_at = ?, updated_at = ?
                        where job_id = ? and status = 'QUEUED'
                        """,
                Timestamp.from(now),
                Timestamp.from(now),
                jobId
        );
    }

    public void markSucceeded(String jobId, String resultJson) {
        Instant now = Instant.now();
        jdbcTemplate.update(
                """
                        update ai_sync_job
                        set status = 'SUCCEEDED', result_json = ?, completed_at = ?, updated_at = ?
                        where job_id = ?
                        """,
                resultJson,
                Timestamp.from(now),
                Timestamp.from(now),
                jobId
        );
    }

    public void markFailed(String jobId, String errorMessage) {
        Instant now = Instant.now();
        jdbcTemplate.update(
                """
                        update ai_sync_job
                        set status = 'FAILED', error_message = ?, completed_at = ?, updated_at = ?
                        where job_id = ?
                        """,
                errorMessage,
                Timestamp.from(now),
                Timestamp.from(now),
                jobId
        );
    }

    public Optional<AiSyncJobRecord> findById(String jobId) {
        List<AiSyncJobRecord> rows = jdbcTemplate.query(
                """
                        select job_id, sync_type, requested_limit, status, result_json, error_message,
                               created_at, started_at, completed_at
                        from ai_sync_job
                        where job_id = ?
                        """,
                (rs, rowNum) -> new AiSyncJobRecord(
                        rs.getString("job_id"),
                        rs.getString("sync_type"),
                        (Integer) rs.getObject("requested_limit"),
                        rs.getString("status"),
                        rs.getString("result_json"),
                        rs.getString("error_message"),
                        toInstant(rs.getTimestamp("created_at")),
                        toInstant(rs.getTimestamp("started_at")),
                        toInstant(rs.getTimestamp("completed_at"))
                ),
                jobId
        );
        return rows.stream().findFirst();
    }

    public boolean hasActiveJob(String syncType) {
        Integer count = jdbcTemplate.queryForObject(
                """
                        select count(*)
                        from ai_sync_job
                        where sync_type = ? and status in ('QUEUED', 'RUNNING')
                        """,
                Integer.class,
                syncType
        );
        return count != null && count > 0;
    }

    private static Instant toInstant(Timestamp value) {
        return value == null ? null : value.toInstant();
    }

    public record AiSyncJobRecord(
            String jobId,
            String syncType,
            Integer requestedLimit,
            String status,
            String resultJson,
            String errorMessage,
            Instant createdAt,
            Instant startedAt,
            Instant completedAt
    ) {
    }
}
