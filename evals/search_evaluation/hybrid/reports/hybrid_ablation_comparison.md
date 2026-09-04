# Hybrid Search Ablation

100 paired queries; 10,000 bootstrap samples; seed 42.

Constraint satisfaction is recomputed independently from `product_snapshot.csv`; it is not copied from the API response.

| Configuration | Strict Hit@5 | Graded NDCG@5 | Graded Recall@5 | Constraint satisfaction@5 | Query success@5 | P95 ms |
|---|---:|---:|---:|---:|---:|---:|
| Image-only | 0.860 | 0.693 | 0.780 | 0.274 | 0.870 | 1298 |
| Text-only | 0.570 | 0.457 | 0.548 | 0.430 | 0.740 | 5478 |
| Image + text post-filter | 0.960 | 0.890 | 0.895 | 0.960 | 0.960 | 1299 |
| Fusion, rerank off | 0.920 | 0.855 | 0.858 | 0.446 | 0.960 | 892 |
| Fusion, rerank on | 0.660 | 0.510 | 0.663 | 0.418 | 0.840 | 2344 |

## Paired bootstrap 95% CI

Delta is right minus left.

| Comparison | Metric | Delta | CI 95% |
|---|---|---:|---:|
| text_only_minus_image_only | strict_hit@5 | -0.2900 | [-0.4200, -0.1600] |
| text_only_minus_image_only | graded_ndcg@5 | -0.2359 | [-0.3441, -0.1235] |
| text_only_minus_image_only | graded_recall@5 | -0.2320 | [-0.3520, -0.1083] |
| text_only_minus_image_only | constraint_satisfaction@5 | +0.1563 | [+0.0863, +0.2277] |
| text_only_minus_image_only | constraint_success@5 | -0.1300 | [-0.2400, -0.0200] |
| image_post_filter_minus_image_only | strict_hit@5 | +0.1000 | [+0.0500, +0.1600] |
| image_post_filter_minus_image_only | graded_ndcg@5 | +0.1971 | [+0.1391, +0.2579] |
| image_post_filter_minus_image_only | graded_recall@5 | +0.1150 | [+0.0600, +0.1751] |
| image_post_filter_minus_image_only | constraint_satisfaction@5 | +0.6860 | [+0.6320, +0.7360] |
| image_post_filter_minus_image_only | constraint_success@5 | +0.0900 | [+0.0400, +0.1500] |
| fusion_no_rerank_minus_image_only | strict_hit@5 | +0.0600 | [-0.0300, +0.1500] |
| fusion_no_rerank_minus_image_only | graded_ndcg@5 | +0.1622 | [+0.0780, +0.2437] |
| fusion_no_rerank_minus_image_only | graded_recall@5 | +0.0783 | [-0.0050, +0.1658] |
| fusion_no_rerank_minus_image_only | constraint_satisfaction@5 | +0.1723 | [+0.1162, +0.2307] |
| fusion_no_rerank_minus_image_only | constraint_success@5 | +0.0900 | [+0.0200, +0.1600] |
| fusion_rerank_minus_image_only | strict_hit@5 | -0.2000 | [-0.3300, -0.0700] |
| fusion_rerank_minus_image_only | graded_ndcg@5 | -0.1832 | [-0.2876, -0.0759] |
| fusion_rerank_minus_image_only | graded_recall@5 | -0.1170 | [-0.2342, +0.0023] |
| fusion_rerank_minus_image_only | constraint_satisfaction@5 | +0.1443 | [+0.0827, +0.2082] |
| fusion_rerank_minus_image_only | constraint_success@5 | -0.0300 | [-0.1300, +0.0700] |
| image_post_filter_minus_text_only | strict_hit@5 | +0.3900 | [+0.2800, +0.5000] |
| image_post_filter_minus_text_only | graded_ndcg@5 | +0.4330 | [+0.3413, +0.5192] |
| image_post_filter_minus_text_only | graded_recall@5 | +0.3470 | [+0.2420, +0.4517] |
| image_post_filter_minus_text_only | constraint_satisfaction@5 | +0.5297 | [+0.4403, +0.6170] |
| image_post_filter_minus_text_only | constraint_success@5 | +0.2200 | [+0.1300, +0.3200] |
| fusion_no_rerank_minus_text_only | strict_hit@5 | +0.3500 | [+0.2600, +0.4400] |
| fusion_no_rerank_minus_text_only | graded_ndcg@5 | +0.3980 | [+0.3239, +0.4724] |
| fusion_no_rerank_minus_text_only | graded_recall@5 | +0.3103 | [+0.2250, +0.4000] |
| fusion_no_rerank_minus_text_only | constraint_satisfaction@5 | +0.0160 | [-0.0293, +0.0608] |
| fusion_no_rerank_minus_text_only | constraint_success@5 | +0.2200 | [+0.1400, +0.3000] |
| fusion_rerank_minus_text_only | strict_hit@5 | +0.0900 | [-0.0100, +0.1900] |
| fusion_rerank_minus_text_only | graded_ndcg@5 | +0.0527 | [-0.0192, +0.1249] |
| fusion_rerank_minus_text_only | graded_recall@5 | +0.1150 | [+0.0225, +0.2100] |
| fusion_rerank_minus_text_only | constraint_satisfaction@5 | -0.0120 | [-0.0600, +0.0348] |
| fusion_rerank_minus_text_only | constraint_success@5 | +0.1000 | [+0.0100, +0.1900] |
| fusion_no_rerank_minus_image_post_filter | strict_hit@5 | -0.0400 | [-0.1000, +0.0200] |
| fusion_no_rerank_minus_image_post_filter | graded_ndcg@5 | -0.0350 | [-0.0905, +0.0184] |
| fusion_no_rerank_minus_image_post_filter | graded_recall@5 | -0.0367 | [-0.0992, +0.0233] |
| fusion_no_rerank_minus_image_post_filter | constraint_satisfaction@5 | -0.5137 | [-0.5872, -0.4392] |
| fusion_no_rerank_minus_image_post_filter | constraint_success@5 | +0.0000 | [-0.0500, +0.0500] |
| fusion_rerank_minus_image_post_filter | strict_hit@5 | -0.3000 | [-0.4000, -0.2000] |
| fusion_rerank_minus_image_post_filter | graded_ndcg@5 | -0.3803 | [-0.4567, -0.3011] |
| fusion_rerank_minus_image_post_filter | graded_recall@5 | -0.2320 | [-0.3278, -0.1358] |
| fusion_rerank_minus_image_post_filter | constraint_satisfaction@5 | -0.5417 | [-0.6208, -0.4607] |
| fusion_rerank_minus_image_post_filter | constraint_success@5 | -0.1200 | [-0.2000, -0.0400] |
| fusion_rerank_minus_fusion_no_rerank | strict_hit@5 | -0.2600 | [-0.3500, -0.1700] |
| fusion_rerank_minus_fusion_no_rerank | graded_ndcg@5 | -0.3453 | [-0.4101, -0.2798] |
| fusion_rerank_minus_fusion_no_rerank | graded_recall@5 | -0.1953 | [-0.2773, -0.1170] |
| fusion_rerank_minus_fusion_no_rerank | constraint_satisfaction@5 | -0.0280 | [-0.0520, -0.0060] |
| fusion_rerank_minus_fusion_no_rerank | constraint_success@5 | -0.1200 | [-0.1900, -0.0500] |
