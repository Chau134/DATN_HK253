# Paired Top-20 Pooling Artifacts

This directory contains reproducible intermediate artifacts for the paired simple/challenging
Image Search evaluation. These files are retained for auditability; they are not the final metric
outputs.

- `paired_top20_pool_review_pending.csv`: full 935-pair incremental audit pool.
- `paired_top20_pool_human_review_pending.csv`: original 36-pair human-review queue.
- `paired_top20_pool_auto_rule.csv`: 899 new pairs labeled by `metadata_rule_v1`.
- `paired_top20_pool_review.html`: local visual-review interface.
- `paired_top20_pool_summary_by_query.csv`: per-query pooling counts.

The completed human export is `../../../data/paired_top20_pool_reviewed.csv`. The canonical merged
ground truth is `../../../data/ground_truth_image_paired.csv`. Final metrics and paired comparisons
remain one level above in `../` and under `../../../challenging/reports/`.
