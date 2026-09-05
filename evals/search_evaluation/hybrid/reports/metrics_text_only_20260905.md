# Hybrid Search Evaluation

- Queries: 100
- HTTP success: 100.0%
- Strict Hit@1/5/10/20: 26.0% / 58.0% / 66.0% / 72.0%
- Strict MRR: 0.3879
- Graded NDCG@5/10/20: 0.5040 / 0.5338 / 0.5588
- Filter parse complete: 96.0%
- Latency p50/p95: 3344/5815 ms

## Transformation breakdown

| Type | N | Strict Hit@1 | Hit@5 | Hit@20 | Strict MRR | Graded NDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| color | 17 | 47.1% | 82.4% | 94.1% | 0.5975 | 0.7370 |
| color_material | 11 | 72.7% | 81.8% | 90.9% | 0.7591 | 0.7691 |
| color_usage | 11 | 18.2% | 81.8% | 90.9% | 0.4401 | 0.5400 |
| material | 17 | 11.8% | 41.2% | 58.8% | 0.2731 | 0.3199 |
| material_usage | 11 | 18.2% | 54.5% | 63.6% | 0.3387 | 0.4115 |
| price | 16 | 6.2% | 37.5% | 56.2% | 0.1553 | 0.4728 |
| usage | 17 | 17.6% | 41.2% | 58.8% | 0.2701 | 0.3495 |
