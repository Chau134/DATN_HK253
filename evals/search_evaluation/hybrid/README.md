# Hybrid Search Evaluation (Image + Text)

This directory contains a controlled 100-query evaluation set for
`POST /search/hybrid`. Gender and brand testcases are excluded.

## Controlled counterfactual design

Each query is anchored to one source product in the 1,000-product database.
`target_product_id` equals `source_product_id`, so the expected top result is
known. For color/material testcases, the reference image must be edited away
from the database metadata while the text asks for the original database
attribute. This tests whether text can override the changed visual attribute
without changing product identity or style.

Example:

- Database target: black cotton top.
- Edited reference: the same top changed to red satin.
- Query: `tìm áo giống ảnh nhưng đổi sang màu đen, chất liệu cotton`.
- Expected grade-3 product: the original black cotton database product.

## Distribution and image requirements

| Difficulty | Transformation | Queries | Final image source |
| --- | --- | ---: | --- |
| easy | `color` | 17 | supplied edited URL |
| easy | `material` | 17 | supplied edited URL |
| medium | `usage` | 17 | reuse approved medium URL |
| medium | `price` | 16 | reuse approved medium URL |
| hard | `color_material` | 11 | supplied edited URL |
| hard | `color_usage` | 11 | supplied edited URL |
| hard | `material_usage` | 11 | supplied edited URL |
| **Total** | | **100** | **100 ready** |

The 33 hard image-search URLs are retained as edit sources, but the hybrid
queries use the new edited URLs supplied in
`data/reference_image_requirements.csv`. The 34 easy source images come from
the database image set. The 33 medium URLs are reused directly without edits.

## Supplied edited image URLs

All 67 edited image URLs have been supplied in
`data/reference_image_requirements.csv`. Each row contains:

- `source_image_url`: image to edit; keep this value unchanged.
- `image_edit_request`: exact requested visual edit.
- `required_reference_color` / `required_reference_material`: what the edited
  reference image must show.
- `target_text_color` / `target_text_material`: original database attribute
  requested by the final text query.
- `new_image_url`: uploaded edited image URL.

After filling `new_image_url`, rerun the generator. Existing supplied URLs are
preserved and copied into `multimodal_queries.csv`:

```powershell
python scripts/05_generate_transform_testcases.py
python scripts/06_validate_reference_images.py
```

During a future partial URL update, structural validation can be run with:

```powershell
python scripts/06_validate_reference_images.py --allow-pending-images
```

## Inputs and outputs

Inputs:

- `data/product_snapshot.csv`
- `../image/data/image_queries.csv`

Outputs:

- `data/reference_image_requirements.csv`
- `data/multimodal_queries.csv`
- `data/sampled_multimodal_items.csv`
- `data/ground_truth_multimodal_candidates.csv`
- `data/ground_truth_multimodal.csv`

## Approved ground truth

The original frozen `data/ground_truth_multimodal.csv` contains 633 approved judgments
for 100 queries. Its grade 0/1/2/3 distribution is 14/480/38/101. Provenance is
preserved per row:

- 100 controlled-counterfactual targets were visually approved at grade 3;
- 154 visual judgments were transferred from the approved Image Search ground truth;
- 379 remaining candidates use conservative `metadata_hybrid_rule_v1` labels
  after text constraints were prevalidated.

All 100 reference images are approved: 67 edited references passed identity,
requested-change, and unintended-change review; 33 references reuse approved
Image Search fixtures. Rebuild and freeze the review with:

```powershell
python scripts/09_build_ground_truth_review.py
python scripts/11_build_review_contact_sheets.py
python scripts/12_complete_ground_truth_review.py
python scripts/10_finalize_ground_truth_review.py `
  --reference-review-csv reports/review/hybrid_reference_review_completed.csv `
  --candidate-review-csv reports/review/hybrid_candidate_review_completed.csv `
  --update-source-status
```

The finalizer rejects unresolved rows and requires every target product to be
approved at grade 3. Review artifacts and the provenance summary are retained
under `reports/review/`.
## Five-way baseline and ablation comparison (extended 2026-08-31)

The four online configurations use the same 100 queries and product snapshot.
The image + text post-filter baseline deterministically replays the frozen
Image-only Top-20, applies exact normalized category/color/material/price/usage
constraints from the evaluation fixture, and preserves image-similarity order.
It does not call text retrieval, fusion, business boosts, or reranking.

The post-filter Top-5 introduced 21 pairs outside the original Hybrid pool. All
21 already had approved labels in the paired Image Search ground truth, so they
were transferred with provenance and no new human or rule label. The extended
`data/ground_truth_multimodal_post_filter_20260831.csv` has 654 approved rows;
its grade 0/1/2/3 distribution is 22/491/40/101.

The online runner checks `/health/ready` and rejects a run when the effective
reranker state differs from the expected state. All source runs completed
100/100 requests with HTTP 200; the offline post-filter replay also covers all
100 queries, with four empty result lists after exact filtering.

| Configuration | Strict Hit@5 | Graded NDCG@5 | Graded Recall@5 | Constraint satisfaction@5 | Query success@5 | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Image-only | 0.860 | 0.693 | 0.780 | 0.274 | 0.870 | 1,298 |
| Text-only | 0.570 | 0.457 | 0.548 | 0.430 | 0.740 | 5,478 |
| Image + text post-filter | 0.960 | 0.890 | 0.895 | 0.960 | 0.960 | 1,299 |
| Fusion, rerank off | 0.920 | 0.855 | 0.858 | 0.446 | 0.960 | 892 |
| Fusion, rerank on | 0.660 | 0.510 | 0.663 | 0.418 | 0.840 | 2,344 |

`constraint_satisfaction@5` is the mean fraction of actually returned Top-5
products that satisfy every non-empty category, color, material, price-bucket,
and usage constraint. `constraint_success@5` is the fraction of queries with at
least one such product in Top-5. Both are recomputed independently by exact
normalized comparison with `product_snapshot.csv`; API-provided filter flags
are not used. The denominator uses the number actually returned (at most five),
while query success prevents an underfilled result list from appearing better.

The paired bootstrap uses 10,000 query-level resamples with seed 42. Compared
with fusion without rerank, enabling rerank changes Strict Hit@5 by -0.260
(CI 95% [-0.350, -0.170]), Graded NDCG@5 by -0.342
([-0.407, -0.276]), constraint satisfaction@5 by -0.028
([-0.052, -0.006]), and query success@5 by -0.120
([-0.190, -0.050]). The current reranker is therefore not selected. Its
execution was verified by 1,436 result rows carrying `rerank_score` across 93
queries; the rerank-off run contains no such score.

Build the deterministic post-filter artifact, then reproduce the five-way report:

```powershell
python scripts/07b_build_image_post_filter.py
python scripts/13_compare_ablation.py `
  --ground-truth-csv data/ground_truth_multimodal_post_filter_20260831.csv `
  --run "image_only=data/search_results_image_only_20260828.csv;reports/hybrid_responses_image_only_20260828.jsonl" `
  --run "text_only=data/search_results_text_only_20260828.csv;reports/hybrid_responses_text_only_20260828.jsonl" `
  --run "image_post_filter=data/search_results_image_post_filter_20260831.csv;reports/hybrid_responses_image_post_filter_20260831.jsonl" `
  --run "fusion_no_rerank=data/search_results_fusion_no_rerank_20260828.csv;reports/hybrid_responses_fusion_no_rerank_20260828.jsonl" `
  --run "fusion_rerank=data/search_results_fusion_rerank_20260828.csv;reports/hybrid_responses_fusion_rerank_20260828.jsonl"
```

The machine-readable result, summary table, and full six-pair confidence
interval table are stored in `reports/hybrid_ablation_comparison.json`,
`reports/hybrid_ablation_summary.csv`, and
`reports/hybrid_ablation_comparison.md`.
