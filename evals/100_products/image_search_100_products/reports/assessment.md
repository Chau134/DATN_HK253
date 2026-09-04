# Assessment: image search trên bộ 100 sản phẩm

## Bối cảnh chạy

- Endpoint: `http://localhost:8000/search/image`
- Phạm vi: 100 ảnh catalog ưu tiên `MAIN`, mỗi sản phẩm một ảnh.
- Loại ảnh query: `{"MAIN": 96, "FLAT_1": 4}`.
- Image-search readiness: ready.
- HTTP thành công: 100/100.

## Kết quả

- Hit@1: 99.0%
- Hit@3: 100.0%
- Hit@5: 100.0%
- MRR: 0.9950
- Miss: 0
- Empty results: 0
- Query có duplicate ID: 0
- Query có Top-1/Top-2 đồng điểm: 1
- Search latency p50/p95/max: 2731/2982/5156 ms
- Query dùng fallback/full-image crop: 100/100

## Nhận định

1. Toàn bộ ảnh được tải và endpoint xử lý thành công; baseline không bị nhiễu bởi lỗi vận hành.
2. Tất cả source product đều xuất hiện trong Top 5.
3. Có 1 source product không đứng hạng 1. Ví dụ: main-073 (rank 2).
   Trong đó 1 case có source product đồng điểm với Top 1; thứ tự hiện tại phụ thuộc tie-break không mang ngữ nghĩa.
4. Đây là identity/ingestion acceptance test: ảnh query chính là ảnh catalog đã dùng để index. Kết quả cao chứng minh pipeline tải ảnh, embedding, Qdrant và dedupe hoạt động, nhưng chưa chứng minh khả năng tìm kiếm bằng ảnh chụp thực tế hoặc ảnh ngoài catalog.
5. Có 4 sản phẩm thiếu ảnh MAIN nên runner dùng ảnh ưu tiên kế tiếp (FLAT_1 rồi MODEL_1). Đây là data-quality gap cần được sửa ở catalog ingestion.
6. Gate tiếp theo phải dùng ảnh cross-view và ảnh biến đổi (crop, nén, nền khác, occlusion), sau đó dùng ground truth relevance theo nhóm sản phẩm tương tự để đo Recall/NDCG thay vì chỉ self-hit.

## Acceptance gate: PASS

- [x] `complete_100_cases`
- [x] `image_capability_ready`
- [x] `http_success_100_percent`
- [x] `hit_at_1_at_least_95_percent`
- [x] `hit_at_5_at_least_99_percent`
- [x] `no_empty_results`
- [x] `no_duplicate_product_ids`
- [x] `p95_search_latency_at_most_5_seconds`
