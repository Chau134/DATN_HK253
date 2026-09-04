# Keyword Search Baseline

Thư mục này triển khai baseline keyword/BM25 độc lập để so sánh với Text
Search dùng vector. Baseline dùng đúng snapshot 1.000 sản phẩm, 100 truy vấn và
ground truth v2 trong `../text`; dữ liệu không được sao chép sang một phiên
bản khác.

## Nguyên tắc tránh rò rỉ nhãn

Runner chỉ đọc `query_id` và `query_text` từ query set. Các cột category,
brand, color, material, difficulty và ground truth không được dùng để lọc hoặc
xếp hạng. Ground truth chỉ được đọc bởi bước tính metrics sau khi runner đã
hoàn thành.

Mỗi sản phẩm được biểu diễn bằng văn bản có trọng số từ tên, danh mục, thương
hiệu, màu, chất liệu, giới tính, khoảng giá, mục đích sử dụng và mô tả. Điểm
BM25 được tính offline, không cần AI Service, Qdrant hoặc thư viện bên ngoài.
Quy tắc `minimum_token_coverage` đóng vai trò minimum should match, cho phép
truy vấn bất khả thi trả danh sách rỗng.

## Cấu trúc

```text
keyword_baseline/
  README.md
  configs/keyword_bm25.toml
  data/
  reports/
  scripts/
    keyword_baseline.py
    compare_runs.py
    build_review_packet.py
  tests/
    test_keyword_baseline.py
```

## Chạy kiểm thử tự động

```powershell
python -m unittest discover -s evals/search_evaluation/keyword_baseline/tests -v
```

## Chạy baseline và tính metrics

Từ thư mục gốc repository:

```powershell
python evals/search_evaluation/keyword_baseline/scripts/keyword_baseline.py

python evals/search_evaluation/text/scripts/05_compute_metrics.py `
  --results-csv evals/search_evaluation/keyword_baseline/data/search_results_keyword_bm25.csv `
  --ground-truth-csv evals/search_evaluation/text/data/ground_truth_text_v2.csv `
  --query-set-csv evals/search_evaluation/text/data/text_queries_v2.csv `
  --k-values 5,10,20 `
  --relevance-threshold 1 `
  --output-json evals/search_evaluation/keyword_baseline/reports/metrics_keyword_bm25.json `
  --output-csv evals/search_evaluation/keyword_baseline/reports/metrics_keyword_bm25.csv

python evals/search_evaluation/keyword_baseline/scripts/compare_runs.py
python evals/search_evaluation/keyword_baseline/scripts/build_review_packet.py
```

Output chính:

- `data/search_results_keyword_bm25.csv`: thứ hạng theo từng truy vấn.
- `reports/keyword_bm25_run_metadata.json`: cấu hình và khả năng tái lập.
- `reports/metrics_keyword_bm25.json`: metrics cùng schema với Text Search.
- `reports/compare_keyword_vs_vector_no_rerank.md`: so sánh cặp và khoảng tin
  cậy 95% với Vector Search khi tắt rerank.
- `review/keyword_baseline_review.csv`: packet tập trung cho truy vấn âm bị
  false positive, truy vấn Vector Search miss Top-5 và các chênh lệch NDCG@5
  từ 0,1 trở lên.

## Nội dung cần review

Sau lần chạy đầu, cần review:

1. Các truy vấn âm mà baseline vẫn trả kết quả.
2. Các truy vấn dương trả rỗng hoặc không có relevant product trong Top-5.
3. Các từ được loại trong `STOP_WORDS` và giá trị
   `minimum_token_coverage` trong config.

Không điều chỉnh hai thành phần này trực tiếp trên toàn bộ test set để làm đẹp
metric. Nếu cần hiệu chỉnh, phải tách một tập development/pilot và giữ nguyên
100 truy vấn hiện tại làm tập đánh giá cuối.
