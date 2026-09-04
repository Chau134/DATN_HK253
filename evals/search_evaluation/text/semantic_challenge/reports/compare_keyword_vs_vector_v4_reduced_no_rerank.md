# Keyword BM25 vs Vector Search (rerank off)

Shared positive queries: 90

| Metric | Keyword BM25 | Vector no rerank | Delta | 95% CI | Wins/Ties/Losses |
|---|---:|---:|---:|---:|---:|
| hit@5 | 0.7556 | 1.0000 | +0.2444 | [+0.1556, +0.3333] | 22/68/0 |
| precision@5 | 0.4333 | 0.6289 | +0.1956 | [+0.1244, +0.2733] | 31/54/5 |
| recall@5 | 0.4411 | 0.5802 | +0.1391 | [+0.0774, +0.2071] | 31/54/5 |
| ndcg@5 | 0.6885 | 0.9406 | +0.2520 | [+0.1681, +0.3395] | 33/52/5 |
| mrr | 0.7020 | 0.9630 | +0.2609 | [+0.1742, +0.3498] | 28/60/2 |

## Negative queries

- Keyword empty-result accuracy: 0.8
- Vector empty-result accuracy: 1.0

Positive delta means Vector Search is better than Keyword BM25.
