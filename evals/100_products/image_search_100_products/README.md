# Image search evaluation cho bộ 100 sản phẩm

Bộ eval này lấy đúng 100 sản phẩm trong `database/100.sql`, ưu tiên ảnh `MAIN` của
mỗi sản phẩm làm query và gọi trực tiếp `POST /search/image` của `service-ai`.
Nếu sản phẩm thiếu `MAIN`, runner chọn `FLAT_1`, rồi `MODEL_1`, rồi ảnh có sort order
nhỏ nhất để vẫn giữ đủ 100 case và báo riêng data-quality gap này.

## Chạy

Từ thư mục gốc repository:

```powershell
.\service-ai\.venv\Scripts\python.exe evals\image_search_100_products\run_eval.py
```

Các tùy chọn thường dùng:

```powershell
.\service-ai\.venv\Scripts\python.exe evals\image_search_100_products\run_eval.py `
  --base-url http://localhost:8000 `
  --top-k 5 `
  --concurrency 2 `
  --timeout 60
```

- `--prepare-only`: chỉ trích xuất 100 test case từ SQL.
- `--report-only`: dựng lại báo cáo từ `data/results.jsonl`.
- `--force-download`: bỏ qua cache ảnh và tải lại từ URL catalog.

## Metrics và acceptance gate

Runner đo Hit@1/3/5, MRR, lỗi tải ảnh/HTTP, empty result, duplicate product ID,
fallback detection và latency p50/p95/max. Gate mặc định yêu cầu đủ 100 case,
image-search ready, HTTP thành công 100%, Hit@1 >= 95%, Hit@5 >= 99%, không có
empty/duplicate và p95 search latency <= 5 giây. Báo cáo cũng ghi nhận score tie
giữa Top-1/Top-2 để tách lỗi retrieval thực sự khỏi tie-break không ổn định.

`data/` chứa ảnh cache và raw results có thể tái tạo nên được gitignore. Các file
`reports/run_context.json`, `reports/summary.json` và `reports/assessment.md` là
baseline được lưu trong repository.

## Giới hạn cần hiểu đúng

Đây là identity/ingestion acceptance test: ảnh query cũng là ảnh catalog được dùng
để index. Điểm cao xác nhận pipeline image embedding và retrieval hoạt động, nhưng
không đại diện cho ảnh chụp điện thoại, nền khác, crop, occlusion hoặc sản phẩm ngoài
catalog. Các nhóm đó thuộc phase robustness/relevance trong improvement plan.
