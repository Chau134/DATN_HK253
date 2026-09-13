# Keyword/BM25 Baseline

Thư mục này giữ phần hiện thực và test của baseline từ khóa dùng để so sánh với
Vector Search. Baseline chuẩn hóa truy vấn, lọc theo token và xếp hạng BM25;
không dùng embedding hoặc reranker.

Bản chính thức được chạy trên cùng 100 truy vấn và ground truth của Text v4.
Cấu hình và artifact nằm cùng bộ Text để tránh ghép nhầm phiên bản:

- `../text/semantic_challenge/configs/keyword_bm25_v4_reduced.toml`;
- `../text/semantic_challenge/reports/metrics_keyword_bm25_v4_reduced.{json,csv}`;
- `../text/semantic_challenge/reports/search_results_keyword_bm25_v4_reduced.csv`;
- `../text/semantic_challenge/reports/compare_keyword_vs_vector_v4_reduced_no_rerank.{json,md}`.

Kết quả chính: Hit@5 0,756, NDCG@5 0,689 và MRR 0,702. Các config, report và
phiếu review standalone cũ trong thư mục này đã được loại bỏ; `scripts/` và
`tests/` được giữ để tái lập baseline.
