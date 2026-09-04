# Keyword BM25 vs Vector Search (rerank off)

Shared positive queries: 30

| Metric | Keyword BM25 | Vector no rerank | Delta | 95% CI | Wins/Ties/Losses |
|---|---:|---:|---:|---:|---:|
| hit@5 | 0.2667 | 0.7667 | +0.5000 | [+0.3333, +0.6667] | 15/15/0 |
| precision@5 | 0.0800 | 0.4000 | +0.3200 | [+0.2133, +0.4333] | 19/11/0 |
| recall@5 | 0.1048 | 0.3147 | +0.2099 | [+0.0994, +0.3382] | 19/11/0 |
| ndcg@5 | 0.1578 | 0.5849 | +0.4272 | [+0.2883, +0.5723] | 19/11/0 |
| mrr | 0.1894 | 0.6756 | +0.4861 | [+0.3243, +0.6450] | 20/10/0 |

## Negative queries

- Keyword empty-result accuracy: None
- Vector empty-result accuracy: None

Positive delta means Vector Search is better than Keyword BM25.
