# Text Search Evaluation

Bộ chính thức gồm 100 truy vấn trên snapshot 1.000 sản phẩm: 90 truy vấn dương
và 10 truy vấn âm. Ground truth được duyệt ở cấp `product_id`; metric nhị phân
dùng ngưỡng relevance 1, còn NDCG giữ grade.

## Cấu hình cuối

- `configs/text_search_v4_reduced.yaml`: Vector Search, rerank tắt;
- `configs/text_search_v4_reduced_rerank.yaml`: cùng pipeline, rerank bật;
- `semantic_challenge/configs/keyword_bm25_v4_reduced.toml`: baseline BM25.

## Artifact chính thức

- `reports/metrics_text_v4_reduced_no_rerank.{json,csv}`;
- `reports/metrics_text_v4_reduced_rerank.{json,csv}`;
- hai tệp `text_v4_reduced_*_run_metadata.json`;
- `semantic_challenge/reports/metrics_keyword_bm25_v4_reduced.{json,csv}`;
- các so sánh v4 trong `semantic_challenge/reports/`.

Vector không rerank đạt Hit@5 1,000, NDCG@5 0,945 và MRR 0,963; bật rerank đạt
0,967/0,903/0,915; BM25 đạt 0,756/0,689/0,702. Vì vậy cấu hình được chọn là
Vector Search không rerank.

Mã sinh testcase, runner và evaluator được giữ trong `scripts/`; test nằm trong
`tests/`. Các cấu hình và báo cáo v1--v3/v2 đã được loại bỏ sau khi khóa v4.
