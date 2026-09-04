# SMTP health isolation evidence

- Run date: 2026-08-30
- Backend: Spring Boot 4.0.6
- Test database: isolated `DACN_test`
- SMTP target in test: `127.0.0.1:1` (intentionally unavailable)
- Targeted result: 3/3 passed
- Full regression result: 102/102 passed in 2 minutes 55 seconds

## Assertions

- `MailHealthIndicator` is absent when `management.health.mail.enabled=false`.
- `/actuator/health` returns HTTP 200 with status `UP`.
- `/actuator/health/readiness` returns HTTP 200 with status `UP`; readiness includes application state, MySQL, and disk space.
- `/actuator/health/liveness` returns HTTP 200 with status `UP`; liveness does not depend on SMTP or other external services.

## Reproduction

```text
.\mvnw.cmd -Dtest=HealthEndpointIntegrationTest test
.\mvnw.cmd test
```