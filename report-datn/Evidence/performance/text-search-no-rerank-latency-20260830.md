# Text Search latency khi tắt rerank — 2026-08-30

## Phạm vi

- Run ID: `text-v4-vector-no-rerank-20260830-latency`
- Bộ đánh giá: `v4-reduced-100`, gồm 90 truy vấn positive và 10 truy vấn negative
- Endpoint: `POST http://localhost:8000/search/text`
- `top_k=20`, chạy tuần tự
- Service instance: `9c5c22904e0a436dac862850e7f821a2`
- Cấu hình yêu cầu rerank tắt và health preflight ghi nhận
  `effective_features.reranker_enabled=false`

Latency được đo end-to-end ở client bằng đồng hồ monotonic, từ ngay trước khi gửi
request đến sau khi đã đọc response body và giải mã JSON. Percentile dùng nội suy
tuyến tính R-7 trên các request thành công. Runner checkpoint artifact sau từng
query và dừng nếu service không sẵn sàng hoặc instance thay đổi.

## Kết quả

| Chỉ số | Kết quả |
|---|---:|
| Request thành công | 100/100 |
| Lỗi | 0 |
| Mean | 1.285,728 ms |
| P50 | 1.000,856 ms |
| P95 | 3.838,283 ms |
| P99 | 4.896,811 ms |
| Max | 5.889,924 ms |

Lượt chạy lại vẫn đạt Hit@5 = 1,000, NDCG@5 = 0,945, MRR = 0,963 trên
90 truy vấn positive và Empty Result Accuracy = 1,000 trên 10 truy vấn negative.
Như vậy khoảng trống bằng chứng của NFR-09 về latency Text Search ở cấu hình được
chọn (vector search, rerank tắt) đã được lấp. Kết quả là phép đo tuần tự trên môi
trường local hiện tại, không đại diện cho tải đồng thời.

## Lệnh thực thi

```powershell
python evals/search_evaluation/text/scripts/04_run_search.py `
  --config evals/search_evaluation/text/configs/text_search_v4_reduced.yaml `
  --top-k 20 `
  --run-id text-v4-vector-no-rerank-20260830-latency

python evals/search_evaluation/text/scripts/05_compute_metrics.py `
  --config evals/search_evaluation/text/configs/text_search_v4_reduced.yaml `
  --k-values 5,10,20
```

Raw artifact có đủ 100 sample tại
`Evidence/performance/text-search-no-rerank-latency-20260830.json`.
