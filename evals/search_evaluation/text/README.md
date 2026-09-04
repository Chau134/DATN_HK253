# Text Search Evaluation

Thư mục này chứa workflow thực thi cho Text Search theo plan ở
[text_search_plan.md](../text_search_plan.md).

## Luồng tạo testcase

### Rebuild từ 1.000 sản phẩm MySQL hiện tại

```powershell
$env:MYSQL_PWD = "<mysql-password>"
python scripts/00_export_mysql_snapshot.py
python scripts/07_generate_balanced_testcases.py --existing-queries data/text_queries.csv
```

Pipeline kiểm tra database có đúng 1.000 sản phẩm rồi sinh 100 testcase:
30 `easy`, 30 `medium`, 30 `hard` và 10 `adversarial`/negative.
Các mức positive lần lượt dùng category; category + 1 thuộc tính; và
category + 3 thuộc tính. Ground truth được đối chiếu trên toàn bộ snapshot,
không chỉ trên 90 sản phẩm được chọn làm source.

Generator mới ghi bộ `v2` vào `text_queries_v2.csv`, `ground_truth_text_v2.csv`
và `ground_truth_text_candidates_v2.csv`; các CSV không có hậu tố được giữ làm
baseline v1. V2 tách material/color/usage thành facet rõ ràng, ghi
`intent_type`, `constraint_semantics`, `expected_behavior`, không cắt ground
truth ở 20 sản phẩm, và chỉ đưa full-intent match đã xác định bằng rule vào
ground truth chính. Partial match nằm trong candidate file với trạng thái
`pending` để review thủ công.

1. Chuẩn bị snapshot sản phẩm đã chuẩn hóa từ `products` và các bảng liên quan như
   `product_categories`/`categories`, với các cột tối thiểu sau khi join/mapping:
   `product_id`, `product_name`, `category`, `brand`, `color`, `material`, `gender`, `price`,
   `usage`, `is_active`.
   Vì database hiện tách `categories` riêng và một số field `usage` chưa trùng tên chuẩn, snapshot
   cần map lại trước khi tạo testcase.
2. Chạy `scripts/01_sample_products.py` để tạo bộ sample stratified theo category.
3. Chạy `scripts/02_generate_queries.py` để tạo query set 90 positive / 10 negative.
4. Chạy `scripts/03_generate_ground_truth_candidates.py` để sinh candidate ground truth cho review.
5. Review thủ công file candidate và xuất ground truth cuối cùng.

## Luồng chạy search và tính metrics

Cần `service-ai` đang chạy (mặc định `http://localhost:8000`) và Qdrant đã index sản phẩm.

6. Chạy `scripts/04_run_search.py` để gọi `POST /search/text` cho từng query và lưu kết quả chuẩn hóa:

   ```bash
   python scripts/04_run_search.py --base-url http://localhost:8000 --top-k 20
   ```

   Với testcase v2:

   ```bash
   python scripts/04_run_search.py --config configs/text_search_v2.yaml --top-k 20
   ```

   Output `data/search_results_text.csv` theo schema chung
   `run_id,query_id,mode,rank,product_id,score,raw_score_json`. Query lỗi được ghi 1 dòng
   `rank=0` với `raw_score_json` chứa `error`. Runner kiểm tra capability readiness trước
   khi chạy, kiểm tra lại mỗi 10 query, dừng nếu process restart/degraded, và checkpoint
   CSV sau từng query.

   Nếu config khai báo `paths.latency_json`, runner đồng thời checkpoint latency
   end-to-end phía client cho từng request và tổng hợp mean/P50/P95/P99 theo nội suy
   R-7. Khi config khai báo `rerank.enabled`, preflight cũng bắt buộc trạng thái
   `effective_features.reranker_enabled` của service trùng với cấu hình để tránh
   gắn nhầm nhãn cho lượt đo.

   Có thể chạy lại riêng negative query và thay chúng trong kết quả hiện tại:

   ```bash
   python scripts/04_run_search.py --top-k 5 --query-type negative --merge-existing
   ```

7. Chạy `scripts/05_compute_metrics.py` để tính metrics so với ground truth:

   ```bash
   python scripts/05_compute_metrics.py --k-values 5,10,20 --relevance-threshold 1
   ```

   Với testcase v2:

   ```bash
   python scripts/05_compute_metrics.py --config configs/text_search_v2.yaml --k-values 5,10,20
   ```

   Output `reports/metrics_text.json` (đầy đủ + breakdown theo category/price_bucket) và
   `reports/metrics_text.csv` (bảng phẳng theo K). Positive query tính Precision@K, Recall@K,
   NDCG@K, MRR; negative query tính Empty Result Accuracy và False Positive Rate@K.
   Report v2 còn có Hit@K, Precision trên số kết quả thực trả,
   Recall ceiling/efficiency, first relevant rank, relevant cardinality và
   breakdown theo intent/constraint/retrieval scope. Với exact-title query, ưu
   tiên Hit@K và MRR thay vì diễn giải Precision@K đơn lẻ.

8. Sinh review sheet cho các Top-K result thực tế:

   ```bash
   python scripts/06_generate_result_review_candidates.py
   ```

   File `data/result_review_candidates.csv` kèm tên, category, brand, màu, chất liệu,
   giới tính, giá và use-case từ payload Qdrant. Chỉ diễn giải positive NDCG sau khi các
   dòng `pending` đã được review và nhập lại vào `ground_truth_text.csv`.

## Cấu trúc

```text
text/
  README.md
  configs/
    text_search.yaml
    text_search_v2.yaml
  data/
  reports/
  scripts/
    common.py
    01_sample_products.py
    02_generate_queries.py
    03_generate_ground_truth_candidates.py
    04_run_search.py
    05_compute_metrics.py
    06_generate_result_review_candidates.py
```

## Ghi chú

File cấu hình `text_search.yaml` dùng syntax JSON hợp lệ để các script có thể đọc bằng thư viện
chuẩn của Python mà không cần thêm dependency.
