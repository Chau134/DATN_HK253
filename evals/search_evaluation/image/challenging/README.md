# Challenging Image Search Query Set

This directory contains the real-world/model half of the paired Image Search evaluation.

- `data/image_queries.csv` contains 100 external images for the same `query_id` and
  `source_product_id` values as `../simple/data/image_queries.csv`.
- 66 images come from the previously curated external model-image set.
- 34 outdoor images supplied on 2026-08-27 complete the paired set.
- Pair comparisons must use `query_id` and keep the catalog snapshot, index, Top-K, and model
  version fixed.

The legacy canonical run under `..` is retained unchanged for traceability. Results from
this directory must use a new run ID and new output files.
