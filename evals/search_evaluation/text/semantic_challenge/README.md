# Text Semantic Challenge v1

Bộ mở rộng này kiểm tra phần mà Vector Search được kỳ vọng có lợi thế hợp lý so với Keyword BM25: hiểu từ đồng nghĩa, cách nói hội thoại, tên vật liệu tương đương và mô tả sản phẩm được diễn đạt lại.

Ba mươi biến thể được cố định trước khi chạy hai hệ thống trên semantic slice. Mỗi biến thể bắt nguồn từ một truy vấn positive của Text v2 và giữ nguyên canonical intent. Bộ v2 vẫn được giữ nguyên để đo khả năng lọc facet; không xóa các trường hợp Keyword BM25 đang làm tốt hơn. Nếu thay đổi truy vấn sau khi xem kết quả thì phải tạo version mới và không ghi đè v1.

## Thiết kế đánh giá

- `canonical_v2`: 100 truy vấn gốc, đo exact title, facet và negative rejection.
- `semantic_challenge_v1`: 30 paraphrase của 30 truy vấn positive gốc.
- `v3-semantic`: hợp của hai lát cắt trên sau khi review, dự kiến 130 truy vấn nếu không có câu bị loại.
- Ground truth của biến thể chỉ được kế thừa từ câu nguồn sau khi reviewer xác nhận hai câu giữ nguyên toàn bộ intent và constraints.
- So sánh chính trên semantic slice dùng paired metrics theo cùng query và cùng ground truth: Hit@5, NDCG@5, MRR, Precision@5 và Recall@5.
- Cấu hình BM25 được đóng băng trước khi chạy. Không thêm synonym riêng cho 30 truy vấn mới.

## Bước 1: tạo candidate và phiếu review

```powershell
python evals/search_evaluation/text/semantic_challenge/scripts/build_semantic_challenge.py
```

Review file `review/semantic_query_review.csv`. Mỗi dòng cần một trong ba quyết định:

- `approve`: câu đề xuất giữ nguyên intent và mọi ràng buộc.
- `revise`: nhập câu thay thế vào `approved_query_text`.
- `reject`: câu không thể coi là tương đương; không đưa vào canonical test.

Ưu tiên xem các dòng `review_risk=high`, đặc biệt các ánh xạ `rayon`/`viscose` và paraphrase exact-title.

## Bước 2: finalize sau review

```powershell
python evals/search_evaluation/text/semantic_challenge/scripts/finalize_semantic_challenge.py
```

Script sẽ từ chối chạy nếu còn `pending`. Output canonical gồm:

- `text/data/text_queries_v3_semantic.csv`
- `text/data/ground_truth_text_v3_semantic.csv`
- `semantic_challenge/data/text_queries_semantic_only_v1.csv`
- `semantic_challenge/data/ground_truth_text_semantic_only_v1.csv`

## Bước 3: chạy Vector Search không rerank

Khởi động `service-ai` với rerank tắt và ghi lại version model/index trong run metadata, sau đó chạy semantic slice:

```powershell
python evals/search_evaluation/text/scripts/04_run_search.py `
  --config evals/search_evaluation/text/configs/text_search_semantic_only_v1.yaml `
  --run-id text-semantic-v1-vector-no-rerank `
  --top-k 20

python evals/search_evaluation/text/scripts/05_compute_metrics.py `
  --config evals/search_evaluation/text/configs/text_search_semantic_only_v1.yaml `
  --k-values 5,10,20
```

Chạy v3 để báo cáo kết quả tổng thể và breakdown theo `evaluation_slice`:

```powershell
python evals/search_evaluation/text/scripts/04_run_search.py `
  --config evals/search_evaluation/text/configs/text_search_v3_semantic.yaml `
  --run-id text-v3-vector-no-rerank `
  --top-k 20
```

## Bước 4: chạy Keyword BM25 đã đóng băng

```powershell
python evals/search_evaluation/keyword_baseline/scripts/keyword_baseline.py `
  --config evals/search_evaluation/text/semantic_challenge/configs/keyword_bm25_semantic_only.toml `
  --run-id keyword-bm25-semantic-v1

python evals/search_evaluation/text/scripts/05_compute_metrics.py `
  --query-set-csv evals/search_evaluation/text/semantic_challenge/data/text_queries_semantic_only_v1.csv `
  --ground-truth-csv evals/search_evaluation/text/semantic_challenge/data/ground_truth_text_semantic_only_v1.csv `
  --results-csv evals/search_evaluation/text/semantic_challenge/reports/search_results_keyword_bm25.csv `
  --output-json evals/search_evaluation/text/semantic_challenge/reports/metrics_keyword_bm25.json `
  --output-csv evals/search_evaluation/text/semantic_challenge/reports/metrics_keyword_bm25.csv `
  --k-values 5,10,20
```

Chỉ kết luận Vector tốt hơn Keyword nếu chênh lệch trên semantic slice có hướng nhất quán và paired bootstrap 95% CI không chứa 0 đối với chỉ số xếp hạng chính. Kết quả v2 vẫn phải được trình bày bên cạnh để tránh che giấu trade-off về facet matching và negative rejection.
