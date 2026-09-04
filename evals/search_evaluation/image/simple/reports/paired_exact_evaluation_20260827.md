# Paired Image Search Exact-Retrieval Evaluation

Runs:

- `image-simple-detail-paired-20260827`
- `image-challenging-external-paired-20260827`

Both runs completed 100/100 queries, returned 2,000 rows, and returned 20 unique products per
query. The two query sets use the same 100 query IDs and source products.

| Metric | Simple/detail | Challenging/external | Delta | Paired bootstrap CI 95% |
|---|---:|---:|---:|---:|
| Exact Hit@1 | 0.980 | 0.930 | -0.050 | [-0.100, -0.010] |
| Exact Hit@5 | 1.000 | 0.970 | -0.030 | [-0.070, 0.000] |
| Exact Hit@10 | 1.000 | 1.000 | 0.000 | unchanged |
| Exact Hit@20 | 1.000 | 1.000 | 0.000 | unchanged |
| Exact MRR | 0.990 | 0.950 | -0.040 | [-0.074, -0.013] |

The three challenging queries missing Exact Hit@5 were `image-q0029` (rank 9), `image-q0064`
(rank 7), and `image-q0096` (rank 7). All challenging queries retrieved the exact source product
within Top 10.

Similarity Recall, NDCG, and mAP are intentionally not compared yet. Their valid comparison
requires pooling candidates from both new runs and reviewing candidates absent from the legacy
pool. The current runner also does not store per-request latency.
