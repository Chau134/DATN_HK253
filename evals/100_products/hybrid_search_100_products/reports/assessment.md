# Đánh giá hybrid search trên bộ 100 sản phẩm

- Endpoint: `http://localhost:8000/search/hybrid`
- Phạm vi: 100 query gồm tên tiếng Việt chính xác và ảnh catalog.
- Hybrid readiness: ready.
- HTTP thành công: 100/100.

## Kết quả

- Hit@1: 100.0%
- Hit@3: 100.0%
- Hit@5: 100.0%
- MRR: 1.0000
- Miss/empty/duplicate: 0/0/0
- Query có source khác hybrid: 0
- Search latency p50/p95/max: 5433/6158/8241 ms

## Acceptance gate: FAIL

- [x] `complete_100_cases`
- [x] `hybrid_capability_ready`
- [x] `http_success_100_percent`
- [x] `hit_at_1_at_least_95_percent`
- [x] `hit_at_5_at_least_99_percent`
- [x] `all_results_are_hybrid`
- [x] `no_empty_results`
- [x] `no_duplicate_product_ids`
- [ ] `p95_search_latency_at_most_5_seconds`

## Giới hạn

Đây là identity/ingestion test vì text và ảnh đều lấy từ chính sản phẩm đã index. Bộ test xác nhận pipeline hybrid hoạt động nhưng chưa đo chất lượng với ảnh ngoài catalog, typo, mô tả tự nhiên hoặc điều kiện text mâu thuẫn với ảnh.
