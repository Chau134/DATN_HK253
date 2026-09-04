# Assessment: text search on the 100-product pilot

## Run context

- Endpoint: `http://localhost:8080/api/search/ai/text`
- Scope: 100-product deterministic robustness suite: accentless, conversational, reordered-keyword, and minor-typo queries.
- Queries: 100 (`{"accentless_title": 25, "conversational_title": 25, "reordered_keywords": 25, "minor_typo": 25}`).
- HTTP success: 100/100.
- Degraded/fallback responses: 0/100.

## Metrics

- Hit@1: 99.0%
- Hit@3: 100.0%
- Hit@5: 100.0%
- Exact source-product Hit@5: 100.0%
- Semantic NDCG@5: 0.9823
- Judgment coverage@5: 100.0%
- MRR: 0.9950
- Misses: 0
- Empty-result queries: 0
- Returned products: 500 (mean 5.00/query)
- Latency p50/p95/max: 999/1195/7248 ms
- Sources: `{"text": 500}`
- Warnings: `{}`

## Findings

1. **The AI path is healthy for this run.** All 100 requests succeeded, all returned results use `ai_source=text`, and no fallback warnings were emitted.
2. **The robustness acceptance gate passed.** Hit@5 is 100.0%, Hit@1 is 99.0%, and 0 queries returned no product.
3. Every query retrieved an acceptable product in Top 5.
4. Breakdown by query transformation: accentless_title: Hit@5=100.0%, MRR=1.000; conversational_title: Hit@5=100.0%, MRR=1.000; minor_typo: Hit@5=100.0%, MRR=0.980; reordered_keywords: Hit@5=100.0%, MRR=1.000.
5. Duplicate catalog titles are evaluated as an acceptable-ID group. The exact source-product rank remains available for variant-level diagnosis.

## Acceptance gate: PASS

- HTTP success = 100%.
- Degraded/fallback responses = 0.
- Acceptable product Hit@1 >= 70% and Hit@5 >= 90%.
- Every query type Hit@5 >= 80%.
- Empty-result queries = 0.
- Duplicate product IDs = 0.
- p95 latency <= 3 seconds (adjust only with an explicit production SLO).
- Semantic NDCG@5 >= 0.90 with 100% judgment coverage.
- Broad use-case and negative queries remain a separate semantic extension.
