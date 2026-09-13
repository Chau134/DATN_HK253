# Hybrid policy comparison

All returned Top-5 pairs are judged; graded metrics are complete for this GT version.

Constraint satisfaction uses only attributes parsed from user query text; all requested fields must pass for a returned product. Plain usage lists use ANY. The legacy exact-fixture value is retained only as a diagnostic.

| Policy | Strict Hit@5 | Graded NDCG@5 | Request-conditioned NDCG@5 | Request-scoped satisfaction@5 | Legacy exact diagnostic | Constraint success@5 | P95 search ms | Unjudged Top-5 pairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy | 0.920 | 0.944 | 0.916 | 0.782 | 0.450 | 1.000 | 2656.8 | 0 |
| production | 0.980 | 0.893 | 0.971 | 1.000 | 0.607 | 1.000 | 1909.3 | 0 |

No Top-5 pair remains unjudged for this comparison. Preserve the reviewed GT version and provenance when reproducing results.

Latency differences across host/container runners or different cache histories are descriptive only. Use the matched load experiments for performance comparison.
