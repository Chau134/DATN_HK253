# Image Search Evaluation

## Directory layout

- `data/`, `scripts/`, `reports/`, and `configs/`: canonical 34 easy + 33 medium + 33 hard
  evaluation and its 2,000 approved judgments.
- `simple/`: the 100-query `DETAIL_1` half of the paired robustness evaluation.
- `challenging/`: the paired external-image half, reusing 66 curated model photos and adding
  34 outdoor photos.

Paired pooling and visual review are run from `simple/scripts/build_paired_pool_review.py`; its
intermediate outputs stay under `simple/reports/pooling/`, while final metrics and comparisons
stay directly under `simple/reports/` and `challenging/reports/`.

## Latest paired robustness evaluation (2026-08-28)

The current paired extension evaluates the same 100 products under two input conditions:

- `simple`: 100 catalog `DETAIL_1` images;
- `challenging`: 66 curated model images and 34 outdoor images.

The merged file `data/ground_truth_image_paired.csv` contains 2,935 approved judgments. It keeps
all 2,000 canonical judgments and adds 36 human-reviewed Top-5 pairs plus 899 deterministic
metadata-rule judgments. At relevance grade >= 2, simple/challenging results are respectively:
Recall@5 0.741/0.721, NDCG@5 0.853/0.810, and mAP 0.775/0.723. See
`simple/reports/paired_similarity_comparison.md` for paired bootstrap confidence intervals and
subgroup results.

## Latency measurement

`04_run_search.py` records two query-level timings on every output row:

- `latency_ms`: client-observed AI Service HTTP time, excluding fixture-image download;
- `end_to_end_latency_ms`: fixture download plus service request, retained for diagnostics.

`05_compute_metrics.py` deduplicates the repeated value to one successful sample per query and
reports sample count, mean, P50, P95, and P99. Percentiles use R-7 linear interpolation. A legacy
CSV without latency produces a zero sample count and null percentile values, never a misleading
zero-millisecond result.

Run the two paired conditions sequentially from this directory:

```powershell
python scripts/04_run_search.py --config simple/configs/image_search_simple.yaml --run-id image-simple-latency
python scripts/04_run_search.py --config challenging/configs/image_search_challenging.yaml --run-id image-challenging-latency
```

Then recompute metrics against `data/ground_truth_image_paired.csv`. This is a single-client latency
measurement; concurrent-load P95 remains a separate performance test.

The supplemental runs on 2026-08-28 completed 100/100 successful requests per condition. Service
HTTP P50/P95/P99 was 767/1,002/3,027 ms for simple and 595/989/1,276 ms for challenging. Outputs:

- `simple/data/search_results_image_simple_latency.csv`;
- `challenging/data/search_results_image_challenging_latency.csv`;
- `simple/reports/metrics_paired_simple_latency.json`;
- `challenging/reports/metrics_paired_challenging_latency.json`.

## Latest official run (2026-08-22)

Run `image-human-top5-rule20-20260822-164228` is the current canonical evaluation:

- 500 Top-5 pairs are human-reviewed;
- 1,500 rank 6–20 pairs use conservative `metadata_rule_v1` labels;
- official binary relevance is `relevance_grade >= 2`;
- 100/100 queries succeeded and every query returned 20 unique products;
- ExactHit@1 = 0.980, ExactHit@5 = 0.990, NDCG@5 = 0.857, mAP = 0.871;
- the full methodology and limitations are in
  `reports/image_evaluation_human_top5_rule20_20260822-164228.md`.

This is a ground-truth rebaseline. Do not interpret metric deltas against the old 2,529-row
metadata baseline as a model-quality delta.

The judgments are pooled from this run's Top 20. Therefore Recall@20 is 1 by construction;
future A/B runs must pool and judge newly retrieved candidates before an absolute comparison.

This directory contains the executable workflow for Image Search evaluation based on
[`image_search_plan.md`](../image_search_plan.md).

## Final Curated Test Set (2026-08-22)

The canonical files are:

- `data/image_queries.csv`: 100 approved image queries.
- `data/ground_truth_image.csv`: approved relevance judgments used by metrics.

The difficulty split is based on the approved query photos, not the legacy automatic mapping:

- 34 `easy`: catalog `DETAIL_1` photos.
- 33 `medium`: user-supplied external photos corresponding to `MODEL_1` products.
- 33 `hard`: user-supplied external photos corresponding to `MODEL_2` through `MODEL_5` products.

Product names and attributes remain sourced from the MySQL snapshot. External photos use
`source_image_id=external-q####`. Running the legacy testcase generation scripts will overwrite
the curated query set, so only do that when intentionally rebuilding it.

## Testcase Workflow

### Rebuild from the current 1,000-product MySQL catalog

```powershell
$env:MYSQL_PWD = "<mysql-password>"
python scripts/07_export_mysql_snapshot.py
python scripts/08_generate_balanced_testcases.py
```

This rebuild exports all current products and images from MySQL, then creates
100 stratified image queries: 34 `easy` (`MAIN`/flat packshots), 33 `medium`
(`MODEL_*`), and 33 `hard` (`DETAIL_*`). Ground-truth candidates are matched
against the complete 1,000-product snapshot. Metrics include a `difficulty`
breakdown.

0. Build the input snapshot from the source dataset:

   ```bash
   python scripts/00_build_snapshot_from_jsonl.py
   ```

   This reads `data_clean_zara_search_vi.jsonl` at the repo root and writes
   `data/product_snapshot.csv` + `data/product_images.csv`. Line N of the JSONL maps to the
   DB / Qdrant integer `product_id` N (verified against `database/data.sql`). The dataset's
   top-level `category` is only `WOMAN`/`MAN`, so it is stored as `gender`; the real garment
   category (used for stratified sampling) comes from `category_family` (shirt_blouse, dress,
   pants, ...). Skip this step if you already have a snapshot with the fields below.

   Required snapshot fields: `product_id`, `product_name`, `category`, `brand`, `color`,
   `material`, `gender`, `is_active`, and at least one image source through `image_url`,
   `image_urls`, `main_image`, or a separate `product_images.csv`.
1. Run `scripts/01_sample_images.py --products-csv data/product_snapshot.csv
   --product-images-csv data/product_images.csv` to select 100 image queries with stratified
   category sampling.
2. Review `data/image_annotations.csv` and fill `semantic_image_type`, `image_quality`,
   `review_status`, and `notes`.
3. Run `scripts/02_generate_queries.py --sampled-images-csv data/sampled_images.csv` to create
   `data/image_queries.csv`.
4. Run `scripts/03_generate_ground_truth_candidates.py --products-csv data/product_snapshot.csv
   --query-set-csv data/image_queries.csv` to create candidate ground truth rows.
5. Manually review candidate rows and save approved rows to `data/ground_truth_image.csv`
   (keep only `review_status=approved` rows — `05_compute_metrics.py` ignores the rest).

## Search + Metrics Workflow

`service-ai` must be running and Qdrant must contain indexed image vectors.

```bash
python scripts/04_run_search.py --base-url http://localhost:8000 --top-k 20
python scripts/05_compute_metrics.py --k-values 5,10,20 --relevance-threshold 1
```

The runner calls `POST /search/image` with base64 image payloads loaded from `image_url`. Output is
normalized to:

```csv
run_id,query_id,mode,rank,product_id,score,raw_score_json
```

Metrics retain `@5`, `@10`, and `@20` because K follows the product slots presented to the
user rather than the current average result count. They include:

- exact-product retrieval: Exact Hit@K and Exact MRR;
- similar-product ranking: Precision@K, Recall@K, NDCG@K, MRR, and mAP;
- result coverage: Fulfillment@K and Underfill rate@K;
- underfill diagnosis: Precision@returned, returned count, and unique product count.

`Precision@K` always divides by K. `Precision@returned` divides by the number of unique
products actually returned and must only be used as a diagnostic; it does not replace
`Precision@K`. Breakdowns are written by difficulty, category, semantic image type, and image
quality. The JSON report also contains per-query metrics.

NDCG's ideal ranking is built from all graded ground-truth products for the query, not only
from retrieved products. This prevents an underfilled result list from receiving an inflated
NDCG score.

The current official run is `image-human-top5-rule20-20260822-164228`. It returned 20 unique
products for all 100 queries with zero errors. The canonical raw result is
`data/search_results_image.csv`; canonical metrics are `reports/metrics_image.json` and
`reports/metrics_image.csv`.

## Human Ground-Truth Review

The canonical `data/ground_truth_image.csv` contains 2,000 judged query-candidate pairs. Top 5
contains the user's completed review; ranks 6-20 use conservative `metadata_rule_v1` labels.
Label provenance is preserved in the file. Use grade `>=2` as the official binary relevance
threshold; grade 1 contributes only to graded NDCG.

To rebuild a temporary visual review queue from the canonical result:

```powershell
python scripts/09_build_ground_truth_review.py `
  --results-csv data/search_results_image.csv `
  --top-k 20 `
  --output-csv reports/ground_truth_image_review_candidates.csv `
  --output-html reports/image_ground_truth_review.html
```

Open the generated `reports/image_ground_truth_review.html`. Review in this order:

1. `top5`: establishes the primary ranking judgment;
2. `top10`;
3. `top20`.

q0056 was corrected to the user-supplied external photo
`https://res.cloudinary.com/dhtlzqflg/image/upload/v1787384954/q56f_byo5ns.png`; visual
inspection confirms the grey buttoned vest matches source product 1730, and the corrected
query retrieves 1730 at rank 1.

Grades are: 3 = exact SKU, 2 = highly visually similar/substitutable, 1 = weakly related,
0 = not relevant. The HTML stores progress in browser local storage. Use **Xuất CSV đã
review** to download the completed review.

The completed review is retained in `reports/review/ground_truth_image_review_completed.csv` and
`reports/review/image_ground_truth_review_completed.html`. To rebuild the canonical ground truth,
finalize only after every row is `approved` with an explicit grade or `rejected`:

```powershell
python scripts/10_finalize_ground_truth_review.py `
  --review-csv reports/review/ground_truth_image_review_completed.csv `
  --output-csv data/ground_truth_image.csv
```

The finalizer fails if any row remains pending or if any query's source product is not approved
at grade 3. Rejected candidates become judged grade 0. Compute official similarity metrics only
from the finalized file:

```powershell
python scripts/05_compute_metrics.py `
  --results-csv data/search_results_image.csv `
  --ground-truth-csv data/ground_truth_image.csv `
  --k-values 5,10,20 `
  --relevance-threshold 2 `
  --output-json reports/metrics_image.json `
  --output-csv reports/metrics_image.csv
```

## Structure

```text
image/
  README.md
  configs/
    image_search.yaml
  data/
    product_snapshot.csv              # source metadata from MySQL
    product_images.csv                # source catalog-image mapping
    image_queries.csv                 # canonical 100-query test input
    ground_truth_image.csv            # canonical approved answers for metrics
  reports/
  scripts/
    common.py
    00_build_snapshot_from_jsonl.py
    01_sample_images.py
    02_generate_queries.py
    03_generate_ground_truth_candidates.py
    04_run_search.py
    05_compute_metrics.py
```
