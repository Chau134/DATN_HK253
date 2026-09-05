# Hybrid Search Evaluation

- Queries: 100
- HTTP success: 100.0%
- Strict Hit@1/5/10/20: 90.0% / 92.0% / 94.0% / 95.0%
- Strict MRR: 0.9099
- Graded NDCG@5/10/20: 0.8627 / 0.8595 / 0.8709
- Filter parse complete: 93.0%
- Latency p50/p95: 320/737 ms

## Transformation breakdown

| Type | N | Strict Hit@1 | Hit@5 | Hit@20 | Strict MRR | Graded NDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| color | 17 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.9411 |
| color_material | 11 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.9984 |
| color_usage | 11 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.9586 |
| material | 17 | 70.6% | 82.4% | 88.2% | 0.7505 | 0.7352 |
| material_usage | 11 | 100.0% | 100.0% | 100.0% | 1.0000 | 0.9885 |
| price | 16 | 87.5% | 87.5% | 93.8% | 0.8828 | 0.8621 |
| usage | 17 | 82.4% | 82.4% | 88.2% | 0.8301 | 0.6813 |
