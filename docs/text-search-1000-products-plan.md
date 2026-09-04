# Kế hoạch và kết quả cải thiện Text Search trên 1.000 sản phẩm

Cập nhật: 21/08/2026.

Trạng thái hiện tại: P0–P3 đã hoàn tất và đạt toàn bộ quality gate trên một run
không rerank. P4 được hoãn theo yêu cầu; runtime mặc định tiếp tục tắt reranker.

## 1. Kết quả chốt

Run được chọn làm baseline:

- run ID: `text-v2-20260821-180500-no-rerank-v7-4-final`;
- query set: `text_queries_v2.csv`, 90 positive và 10 negative;
- Top-K: 20;
- reranker: tắt;
- HTTP error: 0;
- positive zero-hit: 0;
- Qdrant: 1.000 point, 1.000 unique `product_id`, 100% schema v7;
- canonicalizer: `2026-08-21.4`.

Deployment sau khi chốt dùng image đã rebuild đầy đủ, instance
`9e9bc0ff13bf47b1bbacda880be3e9cd`; health `ready=true` và
`reranker_enabled=false`.

Artifacts:

- `evals/search_evaluation/text/reports/search_results_text_v2_20260821-180500_no_rerank_v7_4_final.csv`;
- `evals/search_evaluation/text/reports/metrics_text_v2_20260821-180500_no_rerank_v7_4_final.json`;
- `evals/search_evaluation/text/reports/metrics_text_v2_20260821-180500_no_rerank_v7_4_final.csv`.

### Quality gate

| Metric | Gate | Kết quả | Trạng thái |
|---|---:|---:|---|
| HTTP success | 100% | 100% | Đạt |
| Exact-title Hit@20 | 1,0000 | 1,0000 | Đạt |
| Exact-title MRR | 1,0000 | 1,0000 | Đạt |
| Facet-single NDCG@20 | >= 0,9000 | 0,9273 | Đạt |
| Facet-all NDCG@20 | >= 0,7800 | 0,8094 | Đạt |
| Overall NDCG@20 | >= 0,8800 | 0,9120 | Đạt |
| Overall MRR | >= 0,9000 | 0,9360 | Đạt |
| Recall efficiency@20 | >= 0,9000 | 0,9360 | Đạt |
| Negative accuracy | >= 0,9000 | 1,0000 | Đạt |
| Positive zero-hit | 0 | 0 | Đạt |
| Error/degraded source | 0 | 0 | Đạt |

Các metric bổ sung của run cuối:

| K | Precision@K | Hit@K | Recall efficiency@K | NDCG@K |
|---:|---:|---:|---:|---:|
| 5 | 0,547 | 0,989 | 0,891 | 0,890 |
| 10 | 0,471 | 1,000 | 0,904 | 0,897 |
| 20 | 0,398 | 1,000 | 0,936 | 0,912 |

Precision@K chỉ là metric phụ vì nhiều query có số relevant nhỏ hơn K.

## 2. Hạng mục đã thực thi

### P0 — Chặn regression exact-title và hard color

- [x] Thêm flag `TEXT_TRUSTED_COLOR_HARD_FILTER_ENABLED`.
- [x] Exact-title lookup không còn bị inferred filter loại bỏ; explicit API filter
  vẫn được tôn trọng.
- [x] Bổ sung regression test cho các màu legacy `purple`, `yellow`,
  `multicolor`, `dark indigo`, `white`.
- [x] Giữ kết quả đúng cho q0042 và q0043.

Kết quả: exact-title Hit@20 và MRR đều bằng 1,0000.

### P1 — Metadata-only migration Qdrant

- [x] Viết `service-ai/scripts/migrate_text_payload_v7_1000.py` với dry-run mặc định,
  `--apply`, backup, checksum, rollback và kiểm tra convergence.
- [x] Migration bằng `set_payload` theo batch; không re-embed vector.
- [x] Đồng bộ `category_keys`, `category_aliases`, `brand_key`, `color_keys`,
  `material_keys`, `use_case_keys`, `size_keys`, `gender_key`, `audience_keys`
  và title tokens.
- [x] 1.000/1.000 point ở schema v7 và canonicalizer `2026-08-21.4`.
- [x] Dry-run sau migration trả `changed_points=0`.

Audit cuối:

| Kiểm tra | Kết quả |
|---|---:|
| Tổng point | 1.000 |
| Unique `product_id` | 1.000 |
| Blank `product_id` | 0 |
| Schema v7 | 1.000 |
| Thiếu `category_keys` | 0 |
| Thiếu `color_keys` | 0 |
| Thiếu `use_case_keys` | 0 |
| Raw material nhưng không có key | 0 |
| Raw usage nhưng không có key | 0 |
| Thiếu `material_keys` do raw material cũng trống | 15 |

Backup gần nhất trước v7.4:

- file: `service-ai/backups/text_payload_before_v7_4_20260821-180200.jsonl`;
- SHA-256: `7724ca7d754c4b9833f006a0589e13eccb6abb659f4aaa08560a38b7c0813a88`.

Sau khi baseline cuối đạt toàn bộ gate, các backup trung gian v7, v7.2 và v7.3
đã được xóa; chỉ giữ bản v7.4 nói trên làm điểm rollback cuối. Thư mục backup
runtime được loại khỏi Git.

### P2 — Query constraints và candidate retrieval

- [x] Màu dictionary confidence cao được hard-filter trên payload v7; màu chỉ do
  LLM suy diễn vẫn là soft signal.
- [x] Canonical hóa các màu catalog legacy về color family mà không làm mất
  exact shade.
- [x] Bổ sung material alias cho Lyocell/Tencel, gai dầu/hemp và ramie.
- [x] Sửa precedence article type cho bodysuit, dress/jumpsuit và từ chỉ màu
  `đậm` để không bị hiểu thành `đầm`.
- [x] Chuẩn hóa nhãn kết hợp `Blazer & áo vest` thành một category không mơ hồ.
- [x] Không để prefix chung `áo kiểu` ghi đè article type cụ thể `dệt kim`.
- [x] Không còn positive zero-hit.

Hai sửa cuối có tác động trực tiếp tới gate:

- q0023: NDCG@20 từ 0,2560 lên 0,6309;
- q0040 và q0090: NDCG@20 lên 1,0000.

### P3 — Negative rejection

- [x] Thêm catalog feasibility check dựa trên cụm từ rõ ràng, không dùng global
  similarity threshold.
- [x] Tách reason `negative_ood` và `negative_impossible`.
- [x] Chặn trước LLM/embedding/Qdrant cho yêu cầu chắc chắn ngoài catalog hoặc
  bất khả thi.
- [x] Có test bảo vệ các truy vấn hợp lệ như `áo khoác chống nước`, `áo chống nắng`.
- [x] Log reason code nhưng không log credential.

Ba false positive cũ q0092, q0093 và q0098 hiện đều trả rỗng. Negative accuracy
tăng từ 0,7000 lên 1,0000; positive Hit@20 vẫn bằng 1,0000.

## 3. Test và kiểm chứng

- `service-ai`: 298 unit test đạt;
- evaluation text: 7 test đạt;
- migration test gồm idempotency, backup và rollback;
- full evaluation cuối: 100 query, 0 HTTP error;
- runtime dùng reranker tắt.

Lệnh chạy lại baseline:

```powershell
cd C:\A\DACN_HK252

python evals/search_evaluation/text/scripts/04_run_search.py `
  --config evals/search_evaluation/text/configs/text_search_v2.yaml `
  --base-url http://localhost:8000 `
  --top-k 20 `
  --run-id "text-v2-<timestamp>-no-rerank" `
  --output-csv "evals/search_evaluation/text/reports/search_results_text_v2_<timestamp>_no_rerank.csv"

python evals/search_evaluation/text/scripts/05_compute_metrics.py `
  --config evals/search_evaluation/text/configs/text_search_v2.yaml `
  --results-csv "evals/search_evaluation/text/reports/search_results_text_v2_<timestamp>_no_rerank.csv" `
  --output-json "evals/search_evaluation/text/reports/metrics_text_v2_<timestamp>_no_rerank.json" `
  --output-csv "evals/search_evaluation/text/reports/metrics_text_v2_<timestamp>_no_rerank.csv" `
  --k-values 5,10,20
```

## 4. P4 — Hoãn reranker A/B

Không chạy A/B reranker trong đợt này theo yêu cầu. `RERANK_ENABLED` mặc định là
`false` trong Docker Compose và baseline trên là kết quả được chọn.

Token Google hiện có trong `.secrets/reranker-access-token` không còn hợp lệ;
smoke check trước khi dừng P4 nhận 401 và service đã fallback, vì vậy không có
report rerank nào được coi là hợp lệ. Readiness của reranker đã được chỉnh để
chỉ báo ready sau khi request kiểm chứng credential thành công.

Khi cần thực hiện P4 sau này:

1. tạo OAuth access token Google mới và cập nhật secret file;
2. bật `RERANK_ENABLED=true` chỉ cho run A/B;
3. xác nhận health có `reranker=true` và một smoke query có `rerank_score`;
4. chạy cùng query set/snapshot/candidate pool;
5. so sánh quality và p50/p95 latency;
6. trả runtime về `RERANK_ENABLED=false` nếu không có cải thiện rõ ràng.

## 5. Definition of done hiện tại

- [x] Evaluation contract v2 và archive v1 được giữ nguyên.
- [x] Qdrant có đủ 1.000 unique products và 100% schema v7.
- [x] Migration idempotent, có backup/checksum/rollback.
- [x] Exact-title không bị inferred filter loại bỏ.
- [x] Không còn positive zero-hit.
- [x] Negative accuracy >= 0,9000.
- [x] Toàn bộ quality gate đạt trong một run không rerank.
- [x] Raw results, aggregate, intent breakdown và per-query report đã được lưu.
- [x] Không ghi Bedrock/Google credential vào tài liệu hoặc report.
- [ ] Reranker A/B — hoãn theo yêu cầu, không phải blocker của baseline hiện tại.
