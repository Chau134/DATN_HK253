# Keyword BM25 vs Vector Search (rerank off)

Shared positive queries: 120

| Metric | Keyword BM25 | Vector no rerank | Delta | 95% CI | Wins/Ties/Losses |
|---|---:|---:|---:|---:|---:|
| hit@5 | 0.8167 | 1.0000 | +0.1833 | [+0.1167, +0.2583] | 22/98/0 |
| precision@5 | 0.4883 | 0.6283 | +0.1400 | [+0.0833, +0.2017] | 32/79/9 |
| recall@5 | 0.4836 | 0.5822 | +0.0986 | [+0.0512, +0.1510] | 32/79/9 |
| ndcg@5 | 0.7625 | 0.9465 | +0.1840 | [+0.1163, +0.2543] | 34/77/9 |
| mrr | 0.7724 | 0.9681 | +0.1957 | [+0.1283, +0.2686] | 29/88/3 |

## Negative queries

- Keyword empty-result accuracy: 0.8
- Vector empty-result accuracy: 1.0

Positive delta means Vector Search is better than Keyword BM25.
