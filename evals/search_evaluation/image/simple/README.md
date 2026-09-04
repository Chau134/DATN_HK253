# Simple Image Search Query Set

This directory contains the clean/detail half of a paired Image Search evaluation.

## Dataset contract

- `data/image_queries.csv` contains 100 queries for the same 100 source products and the same
  `query_id` values as `../data/image_queries.csv`.
- Every query uses the source product's `DETAIL_1` catalog image.
- All rows are normalized to `semantic_image_type=detail`, `image_quality=good`, and
  `difficulty=easy`.
- The 34 original easy/detail rows are retained; the 66 external model-image rows are replaced
  with `DETAIL_1` images of the same `source_product_id`.
- `data/outdoor_image_requests_34.csv` records the 34 supplied outdoor images that were checked
  and approved to complete the challenging half under `../challenging`.

Do not change `query_id` or `source_product_id` in either half. This preserves a one-to-one
pairing so metric differences can be computed per product.

## Evaluation requirements

Run simple and challenging queries against the same catalog snapshot, image index, Top-K, and
model version. Candidate judgments for a model comparison must be pooled from all compared runs
and reviewed before reporting absolute Recall, NDCG, or mAP.

## Paired Top-20 pooling

Generate the incremental review queue with:

```powershell
python scripts/build_paired_pool_review.py
```

The previous ground truth is retained in full: 2,000 approved judgments for the original 34
detail, 33 medium/model, and 33 hard/model queries. The challenging set reuses the same image URLs
for those 66 model queries and replaces only the original 34 detail queries with the supplied
outdoor images.

The union of the new simple and challenging Top-20 runs contains 2,934 unique
`(query_id, product_id)` pairs. Existing ground truth covers 1,999 pairs in that union. Of the 935
new pairs, human review is limited to the 36 previously unlabeled pairs appearing in the Top-5 of
the 34 new outdoor queries. The other 899 new pairs use the same deterministic
`metadata_rule_v1` policy as the previous pool.

Pooling artifacts:

- `reports/pooling/paired_top20_pool_review_pending.csv`: complete 935-row audit list;
- `reports/pooling/paired_top20_pool_human_review_pending.csv`: original 36-row human queue;
- `reports/pooling/paired_top20_pool_auto_rule.csv`: 899 rows labeled by `metadata_rule_v1`;
- `reports/pooling/paired_top20_pool_review.html`: review UI covering all 34 outdoor query IDs; query IDs
  whose Top-5 is already fully labeled display a reuse notice;
- `reports/pooling/paired_top20_pool_summary_by_query.csv`: manual/automatic counts for every query.

Review grades use the existing scale: 3 = exact SKU, 2 = strongly similar/substitutable,
1 = weakly related, and 0 = irrelevant. The 36 required rows have been reviewed and saved at
`../data/paired_top20_pool_reviewed.csv`; all grades are valid. The finalizer treats those rows as
approved after reviewer confirmation, while retaining their original provenance:

```powershell
python scripts/finalize_paired_pool.py
```

The merged ground truth is `../data/ground_truth_image_paired.csv`: 2,935 approved judgments,
including all 2,000 old judgments, 36 new human judgments, and 899 new rule-based judgments.

Final paired outputs:

- `reports/metrics_paired_simple.json`: simple/detail metrics;
- `../challenging/reports/metrics_paired_challenging.json`: challenging/external-image metrics;
- `reports/paired_similarity_comparison.json`: paired deltas, 95% bootstrap confidence intervals,
  and subgroup metrics;
- `reports/paired_similarity_comparison.md`: readable comparison summary.

At relevance grade >= 2, simple versus challenging Recall@5 is 0.741 versus 0.721,
NDCG@5 is 0.853 versus 0.810, and mAP is 0.775 versus 0.723. The comparison uses 10,000 paired
bootstrap samples with seed 42.
