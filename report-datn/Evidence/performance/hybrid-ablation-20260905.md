# Hybrid Search Ablation

100 paired queries; 10,000 bootstrap samples; seed 42.

Constraint satisfaction is recomputed independently from `product_snapshot.csv`; it is not copied from the API response.

| Configuration | Strict Hit@5 | Graded NDCG@5 | Graded Recall@5 | Constraint satisfaction@5 | Query success@5 | P95 ms |
|---|---:|---:|---:|---:|---:|---:|
| Image-only | 0.860 | 0.667 | 0.569 | 0.276 | 0.870 | 953 |
| Text-only | 0.580 | 0.504 | 0.536 | 0.431 | 0.750 | 5815 |
| Image + text post-filter | 0.960 | 0.876 | 0.691 | 0.960 | 0.960 | 953 |
| Fusion, rerank off | 0.920 | 0.863 | 0.723 | 0.450 | 0.960 | 737 |
| Fusion, rerank on | 0.670 | 0.568 | 0.639 | 0.428 | 0.840 | 2425 |

## Paired bootstrap 95% CI

Delta is right minus left.

| Comparison | Metric | Delta | CI 95% |
|---|---|---:|---:|
| text_only_minus_image_only | strict_hit@5 | -0.2800 | [-0.4100, -0.1500] |
| text_only_minus_image_only | graded_ndcg@5 | -0.1631 | [-0.2718, -0.0526] |
| text_only_minus_image_only | graded_recall@5 | -0.0333 | [-0.1405, +0.0720] |
| text_only_minus_image_only | constraint_satisfaction@5 | +0.1547 | [+0.0853, +0.2260] |
| text_only_minus_image_only | constraint_success@5 | -0.1200 | [-0.2300, -0.0100] |
| image_post_filter_minus_image_only | strict_hit@5 | +0.1000 | [+0.0500, +0.1600] |
| image_post_filter_minus_image_only | graded_ndcg@5 | +0.2084 | [+0.1522, +0.2677] |
| image_post_filter_minus_image_only | graded_recall@5 | +0.1220 | [+0.0701, +0.1815] |
| image_post_filter_minus_image_only | constraint_satisfaction@5 | +0.6840 | [+0.6300, +0.7340] |
| image_post_filter_minus_image_only | constraint_success@5 | +0.0900 | [+0.0400, +0.1500] |
| fusion_no_rerank_minus_image_only | strict_hit@5 | +0.0600 | [-0.0300, +0.1500] |
| fusion_no_rerank_minus_image_only | graded_ndcg@5 | +0.1956 | [+0.1127, +0.2759] |
| fusion_no_rerank_minus_image_only | graded_recall@5 | +0.1538 | [+0.0776, +0.2328] |
| fusion_no_rerank_minus_image_only | constraint_satisfaction@5 | +0.1743 | [+0.1177, +0.2328] |
| fusion_no_rerank_minus_image_only | constraint_success@5 | +0.0900 | [+0.0200, +0.1600] |
| fusion_rerank_minus_image_only | strict_hit@5 | -0.1900 | [-0.3200, -0.0600] |
| fusion_rerank_minus_image_only | graded_ndcg@5 | -0.0987 | [-0.2004, +0.0040] |
| fusion_rerank_minus_image_only | graded_recall@5 | +0.0695 | [-0.0273, +0.1681] |
| fusion_rerank_minus_image_only | constraint_satisfaction@5 | +0.1523 | [+0.0893, +0.2182] |
| fusion_rerank_minus_image_only | constraint_success@5 | -0.0300 | [-0.1300, +0.0700] |
| image_post_filter_minus_text_only | strict_hit@5 | +0.3800 | [+0.2700, +0.4900] |
| image_post_filter_minus_text_only | graded_ndcg@5 | +0.3716 | [+0.2793, +0.4611] |
| image_post_filter_minus_text_only | graded_recall@5 | +0.1553 | [+0.0616, +0.2502] |
| image_post_filter_minus_text_only | constraint_satisfaction@5 | +0.5293 | [+0.4407, +0.6160] |
| image_post_filter_minus_text_only | constraint_success@5 | +0.2100 | [+0.1200, +0.3000] |
| fusion_no_rerank_minus_text_only | strict_hit@5 | +0.3400 | [+0.2500, +0.4300] |
| fusion_no_rerank_minus_text_only | graded_ndcg@5 | +0.3587 | [+0.2841, +0.4334] |
| fusion_no_rerank_minus_text_only | graded_recall@5 | +0.1871 | [+0.1149, +0.2657] |
| fusion_no_rerank_minus_text_only | constraint_satisfaction@5 | +0.0197 | [-0.0245, +0.0630] |
| fusion_no_rerank_minus_text_only | constraint_success@5 | +0.2100 | [+0.1300, +0.2900] |
| fusion_rerank_minus_text_only | strict_hit@5 | +0.0900 | [-0.0100, +0.1900] |
| fusion_rerank_minus_text_only | graded_ndcg@5 | +0.0644 | [-0.0113, +0.1400] |
| fusion_rerank_minus_text_only | graded_recall@5 | +0.1028 | [+0.0155, +0.1919] |
| fusion_rerank_minus_text_only | constraint_satisfaction@5 | -0.0023 | [-0.0492, +0.0430] |
| fusion_rerank_minus_text_only | constraint_success@5 | +0.0900 | [+0.0000, +0.1900] |
| fusion_no_rerank_minus_image_post_filter | strict_hit@5 | -0.0400 | [-0.1000, +0.0200] |
| fusion_no_rerank_minus_image_post_filter | graded_ndcg@5 | -0.0128 | [-0.0664, +0.0399] |
| fusion_no_rerank_minus_image_post_filter | graded_recall@5 | +0.0318 | [-0.0246, +0.0865] |
| fusion_no_rerank_minus_image_post_filter | constraint_satisfaction@5 | -0.5097 | [-0.5828, -0.4348] |
| fusion_no_rerank_minus_image_post_filter | constraint_success@5 | +0.0000 | [-0.0500, +0.0500] |
| fusion_rerank_minus_image_post_filter | strict_hit@5 | -0.2900 | [-0.3900, -0.1900] |
| fusion_rerank_minus_image_post_filter | graded_ndcg@5 | -0.3071 | [-0.3833, -0.2286] |
| fusion_rerank_minus_image_post_filter | graded_recall@5 | -0.0525 | [-0.1329, +0.0261] |
| fusion_rerank_minus_image_post_filter | constraint_satisfaction@5 | -0.5317 | [-0.6100, -0.4505] |
| fusion_rerank_minus_image_post_filter | constraint_success@5 | -0.1200 | [-0.2000, -0.0400] |
| fusion_rerank_minus_fusion_no_rerank | strict_hit@5 | -0.2500 | [-0.3400, -0.1600] |
| fusion_rerank_minus_fusion_no_rerank | graded_ndcg@5 | -0.2943 | [-0.3584, -0.2305] |
| fusion_rerank_minus_fusion_no_rerank | graded_recall@5 | -0.0843 | [-0.1488, -0.0228] |
| fusion_rerank_minus_fusion_no_rerank | constraint_satisfaction@5 | -0.0220 | [-0.0480, +0.0020] |
| fusion_rerank_minus_fusion_no_rerank | constraint_success@5 | -0.1200 | [-0.1900, -0.0500] |
