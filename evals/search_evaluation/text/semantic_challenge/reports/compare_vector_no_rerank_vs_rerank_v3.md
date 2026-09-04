# Vector Search: rerank off vs rerank on

Shared positive queries: 120

| Metric | No rerank | Rerank | Delta | 95% CI | Wins/Ties/Losses |
|---|---:|---:|---:|---:|---:|
| hit@5 | 1.0000 | 0.9750 | -0.0250 | [-0.0583, +0.0000] | 0/117/3 |
| precision@5 | 0.6283 | 0.6150 | -0.0133 | [-0.0400, +0.0100] | 7/104/9 |
| recall@5 | 0.5822 | 0.5615 | -0.0207 | [-0.0465, +0.0001] | 7/104/9 |
| ndcg@5 | 0.9465 | 0.9171 | -0.0294 | [-0.0647, +0.0016] | 14/91/15 |
| mrr | 0.9681 | 0.9304 | -0.0377 | [-0.0790, +0.0003] | 6/102/12 |

## Negative queries

- No-rerank empty-result accuracy: 1.0
- Rerank empty-result accuracy: 1.0

Positive delta means reranking is better; negative delta means it is worse.
