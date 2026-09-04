# Cross-service correlation ID evidence

- Run date: 2026-08-30
- Header: `X-Correlation-ID`
- Backend context: SLF4J MDC key `correlationId`
- AI Service context: Python `ContextVar`
- Backend targeted result: 10/10 passed
- AI Service focused result: 3/3 passed
- AI Service full regression result: 430/430 passed

## Implemented behavior

- The Backend preserves a valid incoming correlation ID or generates a UUID when the header is missing or invalid.
- The Backend returns the ID in the response, adds it to log output, and clears MDC after request completion.
- Every Spring-managed `RestClient` forwards the same ID to the AI Service.
- Backend operations without an inbound HTTP request bind one ID for the complete operation, including all retry attempts, then clear MDC.
- The AI Service validates or generates the ID in HTTP middleware, stores it in a request-local `ContextVar`, includes it in JSON logs, and returns it in the response header.
- CORS allows and exposes `X-Correlation-ID` for browser diagnostics.
- Accepted client-provided values are limited to 1--128 ASCII letters, digits, `.`, `_`, and `-`; unsafe values are replaced rather than logged.

## Assertions covered

- Valid incoming IDs are preserved by both services.
- Missing and invalid IDs are replaced with safe generated values.
- Backend MDC and AI request context do not leak after request completion.
- The outbound Backend request contains the current ID.
- A background operation uses one stable ID across three transient retries.
- AI JSON log records contain the request correlation ID.
- Existing Backend AI-client behavior and the complete AI Service test suite do not regress.

## Reproduction

```text
cd service-api-ecommerce
.\mvnw.cmd "-Dtest=CorrelationIdFilterTest,CorrelationIdRestClientConfigurationTest,RestAiServiceClientCorrelationTest,RestAiServiceClientTest" test

cd ..\service-ai
.\.venv\Scripts\python.exe -m pytest tests/integration/test_correlation_id.py tests/unit/test_correlation_logging.py -q
.\.venv\Scripts\python.exe -m pytest -q
```
