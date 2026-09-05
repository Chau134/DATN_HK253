# Hybrid Search Evaluation

- Queries: 100
- HTTP success: 100.0%
- Strict Hit@1/5/10/20: 26.0% / 67.0% / 79.0% / 95.0%
- Strict MRR: 0.4342
- Graded NDCG@5/10/20: 0.5684 / 0.6067 / 0.6377
- Filter parse complete: 93.0%
- Latency p50/p95: 1914/2425 ms

## Transformation breakdown

| Type | N | Strict Hit@1 | Hit@5 | Hit@20 | Strict MRR | Graded NDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| color | 17 | 47.1% | 70.6% | 100.0% | 0.6145 | 0.6890 |
| color_material | 11 | 45.5% | 100.0% | 100.0% | 0.7045 | 0.7848 |
| color_usage | 11 | 45.5% | 90.9% | 100.0% | 0.6318 | 0.6840 |
| material | 17 | 23.5% | 70.6% | 88.2% | 0.4117 | 0.5101 |
| material_usage | 11 | 9.1% | 81.8% | 100.0% | 0.3136 | 0.4384 |
| price | 16 | 6.2% | 31.2% | 93.8% | 0.1972 | 0.6038 |
| usage | 17 | 11.8% | 47.1% | 88.2% | 0.2747 | 0.3423 |
