# Hybrid Search Evaluation

- Queries: 100
- HTTP success: 100.0%
- Strict Hit@1/5/10/20: 94.0% / 96.0% / 96.0% / 96.0%
- Strict MRR: 0.9500
- Graded NDCG@5/10/20: 0.8756 / 0.8404 / 0.8114
- Filter parse complete: 17.0%
- Latency p50/p95: 672/953 ms

## Transformation breakdown

| Type | N | Strict Hit@1 | Hit@5 | Hit@20 | Strict MRR | Graded NDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| color | 17 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.8575 |
| color_material | 11 | 72.7% | 81.8% | 81.8% | 0.7727 | 0.7956 |
| color_usage | 11 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.9586 |
| material | 17 | 82.4% | 88.2% | 88.2% | 0.8529 | 0.8430 |
| material_usage | 11 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.9807 |
| price | 16 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.9037 |
| usage | 17 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.8298 |
