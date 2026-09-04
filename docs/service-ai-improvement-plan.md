# Kế hoạch còn lại — Service AI

Tài liệu này chỉ chứa công việc **chưa hoàn thành**. Các plan chuyên biệt cho text, image, hybrid và
chatbot là nguồn chi tiết; không lặp lại hạng mục đã hoàn tất ở đây.

## P0 — Khắc phục regression Hybrid Search

Plan chi tiết: `docs/hybrid-search-100-products-improvement-plan.md`.

Baseline 100 sản phẩm hiện chỉ đạt Hit@5 54%, có 23 query rỗng và p95 7,27 giây dù text-only và
image-only đều đạt Hit@5 100%. Ưu tiên theo thứ tự:

1. giữ provenance để inferred category/material/brand là soft, explicit request filters vẫn hard;
2. đồng bộ canonical payload và re-index có version cho cả text/image collections;
3. thêm exact-title union, weak-result recovery và benchmark fusion;
4. song song hóa hai retrieval branches sau khi có stage-level metrics.

## P0 — Nghiệm thu managed reranker

Phụ thuộc semantic benchmark trong `docs/text-search-upgrade-plan.md`.

1. Bật Discovery Engine API và cấp quyền
   `discoveryengine.rankingConfigs.rank` cho runtime service account.
2. Chạy A/B bằng Ranking API thật trên runtime/staging.
3. Đo chất lượng tiếng Việt, latency, chi phí và fallback khi Ranking API lỗi.
4. Chốt `RERANK_ENABLED`, model, `RERANK_TOP_K` và quy trình rollback.

## P1 — Cải thiện multi-crop aggregation

Điểm cùng product hiện vẫn chủ yếu được gộp theo max similarity. Cần thử nghiệm:

- `similarity × detection_confidence`;
- support-count boost nhỏ;
- giảm trọng số fallback crop;
- đánh giá riêng ảnh một vật thể, nhiều vật thể, detect sai và không detect.

Chỉ chọn công thức sau khi đo Recall@K/NDCG trên benchmark image không leakage.

## P1 — Mở rộng follow-up theo sản phẩm tham chiếu

Bổ sung case:

- ordinal vượt số kết quả;
- compare hai ordinal;
- “tìm mẫu giống cái thứ 1”;
- session mới không có history;
- Spring Boot timeout hoặc partial context;
- product context thiếu giá, size hoặc availability.

## P1 — Metrics latency và call count

1. Thêm histogram/counter cho understand, embedding, Qdrant, rerank, Spring context và reply.
2. Theo dõi route, `llm_call_count`, `springboot_call_count`, candidate count và zero-result rate.
3. Tách cold/warm request và collection/model version.
4. Xác minh metric trong CI/integration; nghiệm thu p50/p95 trên runtime thật.

## P2 — Cold start và Cloud Run revision

1. So sánh min instances 0 + lazy load với min instances 1/preload.
2. Đo cold/warm latency cho text, image, hybrid và chatbot.
3. Xác nhận revision nhận traffic dùng đúng model, device, vector dimension, collection, reranker,
   YOLO và credential/readiness behavior.
4. Chốt cấu hình dựa trên latency mục tiêu và chi phí vận hành.

## Kiểm tra còn phải thực hiện

### Tự động/integration

1. Reranker fallback và A/B semantic benchmark.
2. Multi-crop aggregation trên ảnh nhiều vật thể/detect sai.
3. Follow-up, comparison và partial product context.
4. Metrics emission, label cardinality và call count.

### Runtime

1. NDCG/MRR/Recall và zero-result theo modality.
2. p50/p95/p99, cold/warm và chi phí provider.
3. Revision/model/collection/readiness verification.
4. Rollback drill cho collection, reranker và revision.
