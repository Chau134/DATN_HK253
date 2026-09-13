# Hybrid Search Ablation

100 paired queries; 10,000 bootstrap samples; seed 42.

Request-scoped constraint satisfaction is recomputed independently from user `query_text` and `product_snapshot.csv`; it is not copied from the API response. Legacy exact-fixture satisfaction is retained only as a diagnostic.

| Configuration | Strict Hit@5 | Graded NDCG@5 | Request-conditioned NDCG@5 | Graded Recall@5 | Request-scoped satisfaction@5 | Legacy exact diagnostic | Query success@5 | P95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Text-only | 0.580 | 0.601 | 0.607 | 0.412 | 0.770 | 0.431 | 0.940 | 5815 |
| Image-only | 0.860 | 0.689 | 0.640 | 0.314 | 0.482 | 0.276 | 0.900 | 953 |
| Fusion, rerank off | 0.920 | 0.924 | 0.905 | 0.635 | 0.779 | 0.450 | 1.000 | 737 |
| Image-conditioned, usage ANY, rerank off | 0.980 | 0.873 | 0.958 | 0.503 | 0.990 | 0.609 | 1.000 | 2105 |
| Image-conditioned, usage ANY, rerank on | 0.730 | 0.708 | 0.789 | 0.467 | 0.992 | 0.579 | 1.000 | 2248 |

## Paired bootstrap 95% CI

Delta is right minus left.

| Comparison | Metric | Delta | CI 95% |
|---|---|---:|---:|
| image_only_minus_text_only | strict_hit@5 | +0.2800 | [+0.1500, +0.4100] |
| image_only_minus_text_only | graded_ndcg@5 | +0.0882 | [+0.0125, +0.1620] |
| image_only_minus_text_only | request_conditioned_ndcg@5 | +0.0332 | [-0.0623, +0.1215] |
| image_only_minus_text_only | graded_recall@5 | -0.0986 | [-0.1631, -0.0349] |
| image_only_minus_text_only | constraint_satisfaction@5 | -0.2880 | [-0.3560, -0.2207] |
| image_only_minus_text_only | constraint_success@5 | -0.0400 | [-0.1100, +0.0300] |
| fusion_no_rerank_minus_text_only | strict_hit@5 | +0.3400 | [+0.2500, +0.4300] |
| fusion_no_rerank_minus_text_only | graded_ndcg@5 | +0.3230 | [+0.2718, +0.3740] |
| fusion_no_rerank_minus_text_only | request_conditioned_ndcg@5 | +0.2983 | [+0.2442, +0.3536] |
| fusion_no_rerank_minus_text_only | graded_recall@5 | +0.2229 | [+0.1719, +0.2771] |
| fusion_no_rerank_minus_text_only | constraint_satisfaction@5 | +0.0088 | [-0.0362, +0.0533] |
| fusion_no_rerank_minus_text_only | constraint_success@5 | +0.0600 | [+0.0200, +0.1100] |
| image_conditioned_no_rerank_minus_text_only | strict_hit@5 | +0.4000 | [+0.3000, +0.5000] |
| image_conditioned_no_rerank_minus_text_only | graded_ndcg@5 | +0.2719 | [+0.2151, +0.3280] |
| image_conditioned_no_rerank_minus_text_only | request_conditioned_ndcg@5 | +0.3511 | [+0.2911, +0.4134] |
| image_conditioned_no_rerank_minus_text_only | graded_recall@5 | +0.0905 | [+0.0401, +0.1431] |
| image_conditioned_no_rerank_minus_text_only | constraint_satisfaction@5 | +0.2200 | [+0.1527, +0.2887] |
| image_conditioned_no_rerank_minus_text_only | constraint_success@5 | +0.0600 | [+0.0200, +0.1100] |
| image_conditioned_rerank_minus_text_only | strict_hit@5 | +0.1500 | [+0.0400, +0.2600] |
| image_conditioned_rerank_minus_text_only | graded_ndcg@5 | +0.1072 | [+0.0588, +0.1568] |
| image_conditioned_rerank_minus_text_only | request_conditioned_ndcg@5 | +0.1819 | [+0.1230, +0.2438] |
| image_conditioned_rerank_minus_text_only | graded_recall@5 | +0.0550 | [+0.0069, +0.1048] |
| image_conditioned_rerank_minus_text_only | constraint_satisfaction@5 | +0.2220 | [+0.1560, +0.2900] |
| image_conditioned_rerank_minus_text_only | constraint_success@5 | +0.0600 | [+0.0200, +0.1100] |
| fusion_no_rerank_minus_image_only | strict_hit@5 | +0.0600 | [-0.0300, +0.1500] |
| fusion_no_rerank_minus_image_only | graded_ndcg@5 | +0.2349 | [+0.1799, +0.2898] |
| fusion_no_rerank_minus_image_only | request_conditioned_ndcg@5 | +0.2652 | [+0.2016, +0.3339] |
| fusion_no_rerank_minus_image_only | graded_recall@5 | +0.3215 | [+0.2609, +0.3848] |
| fusion_no_rerank_minus_image_only | constraint_satisfaction@5 | +0.2968 | [+0.2338, +0.3610] |
| fusion_no_rerank_minus_image_only | constraint_success@5 | +0.1000 | [+0.0400, +0.1600] |
| image_conditioned_no_rerank_minus_image_only | strict_hit@5 | +0.1200 | [+0.0600, +0.1900] |
| image_conditioned_no_rerank_minus_image_only | graded_ndcg@5 | +0.1838 | [+0.1400, +0.2294] |
| image_conditioned_no_rerank_minus_image_only | request_conditioned_ndcg@5 | +0.3179 | [+0.2586, +0.3815] |
| image_conditioned_no_rerank_minus_image_only | graded_recall@5 | +0.1891 | [+0.1362, +0.2426] |
| image_conditioned_no_rerank_minus_image_only | constraint_satisfaction@5 | +0.5080 | [+0.4380, +0.5760] |
| image_conditioned_no_rerank_minus_image_only | constraint_success@5 | +0.1000 | [+0.0400, +0.1600] |
| image_conditioned_rerank_minus_image_only | strict_hit@5 | -0.1300 | [-0.2500, -0.0100] |
| image_conditioned_rerank_minus_image_only | graded_ndcg@5 | +0.0191 | [-0.0404, +0.0799] |
| image_conditioned_rerank_minus_image_only | request_conditioned_ndcg@5 | +0.1487 | [+0.0746, +0.2284] |
| image_conditioned_rerank_minus_image_only | graded_recall@5 | +0.1537 | [+0.0983, +0.2107] |
| image_conditioned_rerank_minus_image_only | constraint_satisfaction@5 | +0.5100 | [+0.4400, +0.5780] |
| image_conditioned_rerank_minus_image_only | constraint_success@5 | +0.1000 | [+0.0400, +0.1600] |
| image_conditioned_no_rerank_minus_fusion_no_rerank | strict_hit@5 | +0.0600 | [+0.0100, +0.1200] |
| image_conditioned_no_rerank_minus_fusion_no_rerank | graded_ndcg@5 | -0.0511 | [-0.0837, -0.0185] |
| image_conditioned_no_rerank_minus_fusion_no_rerank | request_conditioned_ndcg@5 | +0.0527 | [+0.0307, +0.0767] |
| image_conditioned_no_rerank_minus_fusion_no_rerank | graded_recall@5 | -0.1324 | [-0.1835, -0.0852] |
| image_conditioned_no_rerank_minus_fusion_no_rerank | constraint_satisfaction@5 | +0.2112 | [+0.1547, +0.2713] |
| image_conditioned_no_rerank_minus_fusion_no_rerank | constraint_success@5 | +0.0000 | [+0.0000, +0.0000] |
| image_conditioned_rerank_minus_fusion_no_rerank | strict_hit@5 | -0.1900 | [-0.2900, -0.0900] |
| image_conditioned_rerank_minus_fusion_no_rerank | graded_ndcg@5 | -0.2158 | [-0.2530, -0.1775] |
| image_conditioned_rerank_minus_fusion_no_rerank | request_conditioned_ndcg@5 | -0.1165 | [-0.1542, -0.0774] |
| image_conditioned_rerank_minus_fusion_no_rerank | graded_recall@5 | -0.1678 | [-0.2204, -0.1186] |
| image_conditioned_rerank_minus_fusion_no_rerank | constraint_satisfaction@5 | +0.2132 | [+0.1562, +0.2725] |
| image_conditioned_rerank_minus_fusion_no_rerank | constraint_success@5 | +0.0000 | [+0.0000, +0.0000] |
| image_conditioned_rerank_minus_image_conditioned_no_rerank | strict_hit@5 | -0.2500 | [-0.3400, -0.1600] |
| image_conditioned_rerank_minus_image_conditioned_no_rerank | graded_ndcg@5 | -0.1647 | [-0.1984, -0.1300] |
| image_conditioned_rerank_minus_image_conditioned_no_rerank | request_conditioned_ndcg@5 | -0.1692 | [-0.2041, -0.1342] |
| image_conditioned_rerank_minus_image_conditioned_no_rerank | graded_recall@5 | -0.0354 | [-0.0628, -0.0099] |
| image_conditioned_rerank_minus_image_conditioned_no_rerank | constraint_satisfaction@5 | +0.0020 | [-0.0040, +0.0100] |
| image_conditioned_rerank_minus_image_conditioned_no_rerank | constraint_success@5 | +0.0000 | [+0.0000, +0.0000] |
