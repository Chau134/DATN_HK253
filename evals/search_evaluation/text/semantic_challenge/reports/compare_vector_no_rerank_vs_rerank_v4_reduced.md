# Vector Search: rerank off vs rerank on

Shared positive queries: 90

| Metric | No rerank | Rerank | Delta | 95% CI | Wins/Ties/Losses |
|---|---:|---:|---:|---:|---:|
| hit@5 | 1.0000 | 0.9667 | -0.0333 | [-0.0778, +0.0000] | 0/87/3 |
| precision@5 | 0.6289 | 0.6089 | -0.0200 | [-0.0533, +0.0089] | 4/78/8 |
| recall@5 | 0.5802 | 0.5522 | -0.0280 | [-0.0622, -0.0013] | 4/78/8 |
| ndcg@5 | 0.9406 | 0.9026 | -0.0380 | [-0.0823, +0.0007] | 9/68/13 |
| mrr | 0.9630 | 0.9146 | -0.0484 | [-0.0994, -0.0009] | 5/74/11 |

## Negative queries

- No-rerank empty-result accuracy: 1.0
- Rerank empty-result accuracy: 1.0

Positive delta means reranking is better; negative delta means it is worse.
