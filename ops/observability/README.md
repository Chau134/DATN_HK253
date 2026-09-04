# Text-search observability

The root Compose file provides an optional `observability` profile containing
Prometheus and Grafana:

```powershell
$env:MYSQL_ROOT_PASSWORD = "<local password>"
$env:GRAFANA_ADMIN_PASSWORD = "<local Grafana password>"
docker compose --profile observability up -d
```

Endpoints:

- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>
- service-ai metrics: `http://service-ai:8000/metrics` inside Compose
- Spring metrics: `http://spring-api:8080/actuator/prometheus` inside Compose

Grafana provisions the `Text Search` dashboard automatically. Prometheus loads
alerts for service availability, text error rate, zero-result rate, p95 above
three seconds, and Spring keyword fallback.

No raw query is used as a Prometheus label. Out-of-catalog rejections are
reported through the bounded
`ecommerce_search_recovery_total{decision="rejected_invalid_catalog_constraint"}`
series.
