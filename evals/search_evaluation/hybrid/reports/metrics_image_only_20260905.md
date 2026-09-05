# Hybrid Search Evaluation

- Queries: 100
- HTTP success: 100.0%
- Strict Hit@1/5/10/20: 65.0% / 86.0% / 92.0% / 96.0%
- Strict MRR: 0.7453
- Graded NDCG@5/10/20: 0.6671 / 0.6591 / 0.6549
- Filter parse complete: 0.0%
- Latency p50/p95: 672/953 ms

## Transformation breakdown

| Type | N | Strict Hit@1 | Hit@5 | Hit@20 | Strict MRR | Graded NDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| color | 17 | 23.5% | 88.2% | 100.0% | 0.4967 | 0.5066 |
| color_material | 11 | 45.5% | 54.5% | 81.8% | 0.5266 | 0.5238 |
| color_usage | 11 | 36.4% | 72.7% | 100.0% | 0.5151 | 0.4991 |
| material | 17 | 52.9% | 76.5% | 88.2% | 0.6544 | 0.6255 |
| material_usage | 11 | 90.9% | 100.0% | 100.0% | 0.9545 | 0.9287 |
| price | 16 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.7897 |
| usage | 17 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.7861 |
