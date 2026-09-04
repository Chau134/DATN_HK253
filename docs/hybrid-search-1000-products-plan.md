# Kế hoạch cải thiện Hybrid Search trên 1.000 sản phẩm

Cập nhật: 25/08/2026. Phạm vi: **chỉ sửa service-ai**. Không thay database, Qdrant collection/index, dữ liệu catalog, API consumer hay bộ testcase. Giữ nguyên hợp đồng POST /search/hybrid; mọi thay đổi phải có feature flag/config để rollback.

## 1. Baseline đã khóa

Run hybrid-20260824T171151Z: 100/100 query multimodal thành công, top_k=20.

| Metric strict (đúng target_product_id) | Kết quả |
| --- | ---: |
| Hit@1 / @5 / @10 / @20 | 81% / 85% / 88% / 96% |
| MRR | 0,8326 |
| NDCG@5 / @20 | 0,8295 / 0,8596 |
| Latency p50 / p95 | 1.609 / 2.015 ms |
| Số kết quả trung bình | 14,87/20 |

Breakdown strict Hit@1: đổi màu 100%; đổi màu + chất liệu 100%; đổi màu + usage 100%; đổi chất liệu 64,7%; đổi chất liệu + usage 81,8%; giá 81,2%; usage 52,9%.

Có 4 query miss khỏi Top-20: q0024, q0026, q0047, q0066; tất cả chứa usage, hai query đồng thời có material. 45/100 query trả dưới 20 sản phẩm, 17/100 trả dưới 5. Do đó Hit@1 cao ở nhóm có filter hẹp phải được xem cùng returned_count và underfill.

Metrics graded theo candidate sinh rule chỉ dùng làm diagnostic; strict target metrics là gate chính cho đến khi ground truth graded được audit trực quan.

## 2. Chẩn đoán service-ai

Luồng hiện tại: query + image -> analyze_query/rule parser (+ LLM khi cần) -> resolve hard/soft constraints -> text vector branch song song image vector branch -> union theo product_id -> weighted fusion + optional rerank -> Top-K.

Service đã có các khả năng cần tận dụng: query parser giá, SearchFilter.use_cases, hard/soft constraint resolution, recovery, lexical fusion, parallel branches, soft attribute boost và reranker flag. Vấn đề là thiếu regression/diagnostic và policy ranking chưa tối ưu cho usage, material và candidate pool hẹp.

1. **Giá cần được quan sát và test đúng.** price.py đã parse range/min/max, nhưng response phân biệt explicit_filters (literal/request) với inferred_filters (rule/LLM). Report trước chỉ đọc explicit filter nên không đủ bằng chứng kết luận parser hỏng.
2. **Usage là soft signal.** Service canonicalize use_cases và cộng một boost hằng số. Boost không thể hiện mức overlap/độ chắc chắn nên dễ bị image/text similarity lấn át.
3. **Candidate pool không adaptive.** Pool cố định, text/image dedupe và union có thể còn ít hơn top_k; recovery hiện chỉ relax inferred hard filter, chưa refill đầy đủ unique SKU.
4. **Fusion dùng trọng số tĩnh.** Image 0,45 / text 0,35 / filter 0,15 / business 0,05 không xét candidate xuất hiện ở một hay hai branch, loại constraint hay confidence parse.
5. **Diagnostic chưa đủ.** Cần ghi rõ parser/hard-soft/recovery/candidate count để phân biệt lỗi parse, không đủ catalog sau filter và lỗi retrieval/ranking.

## 3. Mục tiêu và nguyên tắc

- Strict Hit@1 >= 81%, Hit@5 >= 90%, Hit@20 >= 98%.
- Usage Hit@1 từ 52,9% lên >= 70%; material Hit@1 từ 64,7% lên >= 75%.
- 100% literal price trong fixture tạo đúng min_price và/hoặc max_price.
- Underfill@20 <= 5% khi catalog sau explicit hard filter còn ít nhất 20 SKU.
- P95 end-to-end <= 2,42 giây; HTTP success >= 99%; không giảm Hit@5 của nhóm color quá 1pp.

Không hard-filter từ thuộc tính chỉ suy ra từ ảnh. Hard filter chỉ áp dụng cho literal người dùng nêu rõ hoặc request.filters; inference mơ hồ là soft boost và phải có recovery.

## 4. Kế hoạch triển khai

### Giai đoạn 0 — Quan sát và regression contract

- [ ] Thêm diagnostic nội bộ: parsed_filters, explicit_filters, inferred_filters, hard/soft field, source/confidence, candidate count từng branch, union unique count, returned_count, recovery/refill và latency từng stage.
- [ ] Expose diagnostic an toàn qua debug flag hoặc log/metric; không trả embedding, payload Qdrant, prompt hay credential.
- [ ] Tạo regression fixture từ 100 query: assertion parse field, constraint satisfaction, unique product ID, returned count và target rank.
- [ ] Đo filter_parse_rate theo từng field (price, material, color, use_case), không gộp use-case soft ranking với hard filter.

Files: services/search/service.py, filtering.py, constraints.py, schemas/search.py, core/metrics.py, unit tests query/scoring và integration endpoint tests.

Gate: test hiện có pass; baseline rerun không regression quá 1pp ở strict Hit@5.

### Giai đoạn 1 — Parser và constraint giá

- [ ] Bổ sung unit test price cho: dưới 200k, 200k đến 500k, 500k đến 1 triệu, 1–2 triệu, trên 2 triệu, dấu -, đến, tới, k, tr, triệu, đ, và câu đồng thời có category/material.
- [ ] Chuẩn hóa price bucket thành range số trong filtering.py; rule parser ưu tiên literal price của user trước LLM/request merge.
- [ ] Khóa price rule extraction là deterministic hard constraint và ghi min/max vào explicit_constraint_satisfaction khi user nêu trực tiếp.
- [ ] Nếu giá làm candidate ít hơn top_k, refill chỉ trong cùng price range; không relax giá để làm đầy kết quả. Nếu catalog không đủ, trả constraint_failure_reason rõ ràng.

Gate: toàn bộ fixture giá parse đúng; mọi candidate trả về thỏa price range khi range được parse.

### Giai đoạn 2 — Usage-aware ranking

- [ ] Giữ use_cases là soft constraint mặc định, vì metadata usage có thể thiếu; không hard filter usage trừ khi request API gửi filter explicit và sản phẩm đủ nhiều.
- [ ] Thay boost constant bằng score bounded dựa trên overlap/coverage của use_case_keys, nhân confidence parser. Tách exact overlap và partial overlap, có cap để không đảo thứ tự vô lý.
- [ ] Với query category + usage nhưng không có color/material/price, tăng candidate pool và ưu tiên candidate xuất hiện ở cả text/image trước khi áp usage score.
- [ ] Log use_case_match_ratio, source/confidence và per-candidate satisfaction; audit bốn miss query làm regression bắt buộc.

Gate: usage Hit@1 >= 70%, Hit@5 >= 80%; color/material Hit@5 không giảm quá 1pp.

### Giai đoạn 3 — Adaptive retrieval, dedupe và refill

- [ ] Thêm HYBRID_PRODUCT_OVERFETCH_FACTOR và HYBRID_CANDIDATE_POOL_CAP; initial limit là max(top_k * factor, HYBRID_CANDIDATE_POOL_SIZE, RERANK_TOP_K).
- [ ] Dedupe product_id sau từng branch và sau union. Nếu unique candidate < top_k, tăng limit theo cấp số nhân đến cap hoặc collection cạn.
- [ ] Refill luôn giữ explicit hard filter. Recovery chỉ được relax inferred hard filter theo policy hiện có và phải ghi field bị relax vào response diagnostic.
- [ ] Thêm result_underfilled, refill_rounds và, nếu truy xuất được an toàn, eligible_catalog_count để phân biệt retrieval thiếu với catalog không đủ.
- [ ] Test nhiều image point cùng SKU, text/image overlap, filter hẹp và duplicate elimination.

Gate: underfill@20 <= 5% khi đủ eligible SKU; 100% product ID unique; p95 vẫn trong budget.

### Giai đoạn 4 — Fusion và rerank A/B

- [ ] Giữ formula hiện tại làm A0. A/B một biến mỗi lần: agreement boost cho candidate có cả text + image; material-aware text/filter contribution; usage score Giai đoạn 2; rerank top 20.
- [ ] Chuẩn hóa score theo từng branch trước fusion để distribution của một vector collection không lấn branch còn lại; dùng epsilon để tránh reorder do chênh lệch rất nhỏ.
- [ ] Reranker chỉ xử lý candidate đã qua explicit hard filter; timeout/lỗi phải fallback giữ nguyên thứ tự A0.
- [ ] Chọn cấu hình bằng Hit@1/@5/@20, breakdown usage/material, underfill và latency; không chọn chỉ theo aggregate Hit@1.

Gate: chỉ giữ biến thể khi Hit@5 toàn bộ không thấp hơn baseline, usage/material đạt gate và p95 <= 2,42 giây.

### Giai đoạn 5 — Rollout và rollback

- [ ] Feature flag/config cho mọi policy mới; mặc định giữ A0 cho đến khi full eval pass.
- [ ] Startup log snapshot provider/model, collection, hybrid weights, limits/caps và flags, tuyệt đối không log secret.
- [ ] Theo dõi HTTP/error, parse-by-field, hard/soft/recovery, refill rounds, underfill@K, union candidate size và latency analyze/embed/Qdrant/rerank/total.
- [ ] Timeout + bounded retry/backoff cho embedding/reranker. Rollback bằng tắt flag hoặc khôi phục weights A0; không reindex, sửa database hay thay collection.

## 5. Thứ tự thử nghiệm

| Run | Thay đổi service-ai duy nhất | Mục đích |
|---|---|---|
| H0 | Baseline | Mốc so sánh |
| H1 | Diagnostic + parser giá | Xác nhận filter trước tối ưu ranking |
| H2 | Usage overlap boost | Sửa nhóm usage/miss |
| H3 | Product overfetch + refill | Sửa underfill/coverage |
| H4 | Text-image agreement boost | Cải thiện fusion |
| H5 | Material-aware weights | Cải thiện material |
| H6 | Optional reranker | Chỉ giữ nếu vượt gate quality/latency |

Mỗi run dùng cùng 100 query, top_k=20, model/provider/collection và ground truth. Lưu raw response, config snapshot, commit SHA, per-query rank, filter diagnostic và latency. Không thay collection hoặc query set giữa các run.

## 6. Definition of done

- [ ] Parser giá pass toàn bộ fixture và response phân biệt đúng explicit/inferred filter.
- [ ] Usage score có overlap bounded, unit test, và không regression color/material.
- [ ] Retrieval/refill trả đủ unique Top-K khi catalog sau explicit filter còn đủ sản phẩm.
- [ ] Hit@5 >= 90%, Hit@20 >= 98%, usage Hit@1 >= 70%, material Hit@1 >= 75%.
- [ ] Underfill@20 <= 5% khi catalog đủ; mọi underfill còn lại có lý do diagnostic.
- [ ] P95 <= 2,42 giây, HTTP success >= 99%, có feature flag/fallback/rollback.
- [ ] Unit, integration và full hybrid evaluation pass trên cùng commit/config service-ai.

## 7. Trạng thái triển khai baseline không rerank

Cập nhật: 25/08/2026.

Đã triển khai trong `service-ai`:

- thêm `HYBRID_PRODUCT_OVERFETCH_FACTOR=4` và `HYBRID_CANDIDATE_POOL_CAP=100`;
- candidate limit nội bộ tăng theo `top_k`, vẫn giữ nguyên `top_k` public;
- thêm log summary `candidate_limit`, `returned_count`, `underfilled`;
- usage boost chuyển từ nhị phân sang overlap ratio bounded, có flag
  `HYBRID_USE_CASE_OVERLAP_BOOST_ENABLED` để rollback;
- bổ sung regression cho price literals, usage overlap và candidate overfetch;
- cấu hình baseline đã khóa: `RERANK_ENABLED=false`.

Kiểm chứng tại source:

- unit tests: **320 passed**;
- integration search endpoint tests: **13 passed**;
- Docker image `service-ai` đã build thành công.

Full 100-query evaluation chưa thể hoàn tất trong phiên này vì Bedrock runtime thiếu
`AWS_BEARER_TOKEN_BEDROCK`; `/health/ready` trả 503 với `IncompleteSignatureException`.
Đây là blocker credential, không phải lỗi test hay code. Khi có token hợp lệ, chạy evaluation
bằng `service-ai/docker-compose.yml` với `RERANK_ENABLED=false`, lưu artifact riêng (ví dụ
`hybrid-no-rerank-<timestamp>`) để làm baseline; không dùng root compose đang override
`RERANK_ENABLED=true`. Sau đó có thể bật rerank ở một run khác và đối chiếu chính xác với
baseline này.

## 8. Baseline đã chạy sau triển khai — rerank tắt

Run ID: `hybrid-no-rerank-20260825-0638`.

- 100/100 query HTTP 200, không lỗi.
- Runtime xác nhận `RERANK_ENABLED=false`; không có `rerank_score` trong result.
- 1.487 result rows, trung bình 14,87 sản phẩm/query.
- Filter parse coverage sau khi tính cả merged/inferred filters: 93% (metric cũ 42% chỉ đọc explicit filters).

| Strict metric | Baseline cũ | Baseline mới, rerank tắt | Delta |
|---|---:|---:|---:|
| Hit@1 | 81% | **89%** | +8pp |
| Hit@5 | 85% | **92%** | +7pp |
| Hit@10 | 88% | **95%** | +7pp |
| Hit@20 | 96% | **97%** | +1pp |
| MRR | 0,8326 | **0,9030** | +0,0704 |
| NDCG@5 | 0,8295 | **0,9032** | +0,0737 |
| NDCG@20 | 0,8596 | **0,9177** | +0,0581 |
| Latency p50 / p95 | 1.609 / 2.015 ms | 1.750 / 2.309 ms | +141 / +294 ms |

Breakdown mới: đổi màu Hit@1 100%; đổi màu + chất liệu 100%; đổi màu + usage 100%; đổi chất liệu 70,6%; đổi chất liệu + usage 100%; giá 87,5%; usage 76,5%.

Ba query miss của run mới là `q0002` (price), `q0013` (material), `q0092` (material).
Các miss usage cũ `q0024`, `q0026`, `q0047` đã lên rank 1; `q0066` lên rank 17. Vì vậy
đây là cải thiện tổng thể nhưng chưa được xem là không regression: cần giữ các query miss
này trong regression set trước khi bật rerank.

Artifacts:

- `evals/search_evaluation/hybrid/data/search_results_multimodal_no_rerank_20250825_0638.csv`;
- `evals/search_evaluation/hybrid/reports/hybrid_eval_responses_no_rerank_20250825_0638.jsonl`;
- `evals/search_evaluation/hybrid/reports/metrics_multimodal_no_rerank_20250825_0638.json`;
- `evals/search_evaluation/hybrid/reports/metrics_multimodal_no_rerank_20250825_0638.csv`;
- `evals/search_evaluation/hybrid/reports/hybrid_evaluation_no_rerank_20250825_0638.md`.
