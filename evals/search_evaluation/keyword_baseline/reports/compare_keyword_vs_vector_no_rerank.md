# Keyword BM25 vs Vector Search (rerank off)

Shared positive queries: 90

| Metric | Keyword BM25 | Vector no rerank | Delta | 95% CI | Wins/Ties/Losses |
|---|---:|---:|---:|---:|---:|
| hit@5 | 1.0000 | 0.9889 | -0.0111 | [-0.0333, +0.0000] | 0/89/1 |
| precision@5 | 0.6244 | 0.5467 | -0.0778 | [-0.1222, -0.0400] | 3/66/21 |
| recall@5 | 0.6099 | 0.5706 | -0.0393 | [-0.0659, -0.0148] | 3/66/21 |
| ndcg@5 | 0.9641 | 0.8903 | -0.0738 | [-0.1199, -0.0345] | 6/63/21 |
| mrr | 0.9667 | 0.9357 | -0.0309 | [-0.0754, +0.0111] | 4/77/9 |

## Negative queries

- Keyword empty-result accuracy: 0.8
- Vector empty-result accuracy: 1.0

Positive delta means Vector Search is better than Keyword BM25.
