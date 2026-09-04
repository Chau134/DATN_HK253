# Cập nhật rebaseline ngày 22/08/2026

Run chính thức mới: `image-human-top5-rule20-20260822-164228`.

- Ground truth: 2.000 cặp trong retrieval Top 20; 500 cặp Top 5 do người dùng review và 1.500
  cặp rank 6–20 do `metadata_rule_v1` chấm bảo thủ.
- Ngưỡng relevant chính thức: grade `>=2`; grade 1 chỉ đóng góp cho graded NDCG.
- Full run Bedrock `cohere.embed-v4:0`: 100/100 query thành công, 2.000 kết quả, mọi query có
  đủ 20 product duy nhất, Underfill@5/@10/@20 bằng 0.
- Exact Hit@1 = 0,980; Exact Hit@5 = 0,990; Exact Hit@10/20 = 1,000; NDCG@5 = 0,857;
  NDCG@10 = 0,858; NDCG@20 = 0,932; mAP = 0,871.
- q0029 vẫn là case xấu chính: exact product ở rank 9. q0088 có exact product-id ở rank 2,
  nhưng rank 1 là bản ghi trùng cùng SKU.
- Đây là rebaseline do thay evaluation contract, không phải bằng chứng model tự tăng chất lượng.
  Rank 6–20 vẫn cần review chéo nếu dùng benchmark để công bố hoặc thay embedding model.
- Ground truth được pool từ Top 20 của chính run này nên Recall@20 = 1 theo construction. Mọi A/B
  tiếp theo phải lấy hợp candidate của baseline và biến thể mới rồi judge phần candidate mới.

Artifact chi tiết: `evals/search_evaluation/image/reports/image_evaluation_human_top5_rule20_20260822-164228.md`.

# Kế hoạch cải thiện Image Search trên 1.000 sản phẩm

Cập nhật: 22/08/2026.

Trạng thái: Giai đoạn 1 (overfetch, product dedupe và refill) đã hoàn tất ngày 22/08/2026
và đạt gate coverage trên full run 100 query. Bộ metric mở rộng và công thức NDCG chuẩn
cũng đã được triển khai. Người dùng đã review Top 5; rank 6-20 được gán nhãn bảo thủ bằng
`metadata_rule_v1`. Crop/category A/B vẫn đang chờ.

## 1. Kết luận chẩn đoán

Image search hiện tìm đúng sản phẩm gốc rất tốt ở những vị trí đầu, nhưng chưa trả đủ số
lượng sản phẩm và chưa được đánh giá bằng một ground truth đủ tin cậy cho bài toán “sản
phẩm tương tự”. Vì vậy không nên kết luận đơn giản rằng embedding yếu chỉ từ Recall@K và
mAP hiện tại.

Ba nguyên nhân ưu tiên cao nhất là:

1. **Candidate pool bị khử trùng lặp sau khi đã giới hạn ở 20 vector.** Một sản phẩm có
   nhiều ảnh/vector trong Qdrant. API lấy 20 vector rồi mới giữ điểm cao nhất theo
   `product_id`, làm kết quả chỉ còn trung bình 8,31 sản phẩm dù yêu cầu `top_k=20`.
2. **Ground truth đang được sinh tự động từ metadata, chưa phải đánh giá tương đồng hình
   ảnh của con người.** Mọi sản phẩm cùng category đều có thể được tính là relevant; ngưỡng
   metric hiện nhận cả `relevance_grade=1`.
3. **Ảnh nhiều vật thể chưa được tách.** Runtime đang đặt `YOLO_ENABLED=false`, do đó ảnh
   người mẫu có cả áo và quần được embed như một ảnh duy nhất. Hệ thống không biết người
   dùng muốn tìm vật thể nào nếu không crop trước.

Ưu tiên thực hiện là sửa candidate retrieval và evaluation contract trước, sau đó mới A/B
crop, cách gộp điểm và rerank. Nếu làm ngược thứ tự, metric có thể tăng hoặc giảm do nhãn
sai chứ không phản ánh trải nghiệm tìm kiếm thật.

## 2. Baseline đã xác nhận

Nguồn kết quả lịch sử của mục baseline này đã được hợp nhất sau khi rebaseline; các artifact
timestamp cũ đã được xóa để tránh nhầm với bộ chính thức hiện tại.

- aggregate metrics hiện hành: `evals/search_evaluation/image/reports/metrics_image.json`;
- raw result hiện hành: `evals/search_evaluation/image/data/search_results_image.csv`;
- query: 100 ảnh, gồm 34 easy, 33 medium và 33 hard;
- embedding runtime: Bedrock, model `cohere.embed-v4:0`;
- HTTP success: 100/100, không có query lỗi.

### 2.1. Metric tổng hợp

| Metric | K=5 | K=10 | K=20 |
|---|---:|---:|---:|
| Precision@K | 0,438 | 0,297 | 0,151 |
| Recall@K | 0,139 | 0,172 | 0,174 |
| NDCG@K đã sửa IDCG | 0,746 | 0,654 | 0,556 |
| Fulfillment@K | 0,992 | 0,801 | 0,416 |
| Underfill rate@K | 0,040 | 0,750 | 1,000 |
| Exact Hit@K | 0,980 | 0,990 | 0,990 |

- Exact Hit@1: `0,970`;
- Precision@returned: `0,376`;
- MRR: `0,976`;
- Exact MRR: `0,976`;
- mAP: `0,152`;
- sản phẩm nguồn ở rank 1: 97/100;
- sản phẩm nguồn trong top 5: 98/100;
- ngoại lệ: q0005 ở rank 2, q0029 ở rank 9, q0056 không có trong kết quả trả về.

NDCG cũ từng được báo là 0,914/0,947/0,950 vì IDCG chỉ được tạo từ các kết quả đã trả.
Baseline underfill vì thế được lợi sai. Công thức hiện dùng toàn bộ grade trong ground truth
để tạo IDCG; các giá trị 0,746/0,654/0,556 ở trên mới là baseline có thể so sánh.

### 2.2. Theo độ khó

| Difficulty | Số query | Exact top 1 | Exact top 5 | NDCG@5 | mAP | Số kết quả trung bình |
|---|---:|---:|---:|---:|---:|---:|
| Easy | 34 | 34 | 34 | 0,820 | 0,260 | 8,71 |
| Medium | 33 | 31 | 32 | 0,691 | 0,101 | 7,73 |
| Hard | 33 | 32 | 32 | 0,724 | 0,092 | 8,48 |

Easy dùng `DETAIL_1` lấy từ catalog đã index nên có nguy cơ self-match: ảnh query hoặc một
biến thể gần như giống hệt đã có trong index. Medium/hard dùng góc chụp khác thực tế hơn và
cho thấy mAP giảm mạnh. Vì thế easy hiện là smoke test exact-image, chưa đủ để đại diện cho
ảnh khách hàng tải lên.

### 2.3. Kết quả sau Giai đoạn 1

Run: `image-overfetch4-20260822-141144`, Bedrock `cohere.embed-v4:0`, 100/100 query thành
công, 2.000 result rows.

| Metric | Baseline | Overfetch 4x + refill | Delta |
|---|---:|---:|---:|
| Exact Hit@1 | 0,970 | 0,980 | +0,010 |
| Exact Hit@5 | 0,980 | 0,980 | 0,000 |
| Precision@5 | 0,438 | 0,442 | +0,004 |
| Recall@10 | 0,172 | 0,182 | +0,010 |
| Recall@20 | 0,174 | 0,251 | +0,077 |
| NDCG@5 | 0,746 | 0,750 | +0,004 |
| NDCG@10 | 0,654 | 0,667 | +0,013 |
| NDCG@20 | 0,556 | 0,608 | +0,052 |
| mAP | 0,152 | 0,189 | +0,037 |
| Fulfillment@10 | 0,801 | 1,000 | +0,199 |
| Fulfillment@20 | 0,416 | 1,000 | +0,584 |
| Underfill rate@10 | 0,750 | 0,000 | -0,750 |
| Underfill rate@20 | 1,000 | 0,000 | -1,000 |

`Precision@returned` giảm từ 0,376 xuống 0,255 vì mẫu số nay luôn có đủ 20 sản phẩm và phần
đuôi chứa thêm candidate khó. Đây là diagnostic dự kiến, không phải regression của top 5:
Precision@5, Exact Hit@1, NDCG và mAP đều tăng. Trong 2.000 kết quả mới, 524 kết quả cùng
category bị tính sai do không nằm trong ground truth cắt ở top 30; vì vậy chưa dùng
Precision@returned để quyết định category rerank trước human review.

Runtime của full run: Qdrant p50 49,0 ms, p95 235,8 ms; 80 point ban đầu tạo trung bình
31,83 unique products, tối thiểu 20 và có 3/100 query cần refill. Embedding p50 786,8 ms,
p95 1.453,5 ms.

Artifacts chính thức hiện hành:

- `evals/search_evaluation/image/reports/image_evaluation_human_top5_rule20_20260822-164228.md`;
- `evals/search_evaluation/image/reports/run_image-human-top5-rule20-20260822-164228_summary.json`.

Review artifacts đã hoàn tất:

- `evals/search_evaluation/image/reports/image_ground_truth_review_completed.html`;
- `evals/search_evaluation/image/reports/ground_truth_image_review_completed.csv`;
- `evals/search_evaluation/image/reports/ground_truth_image_review_overrides.csv`;
- builder: `scripts/09_build_ground_truth_review.py`;
- validator/finalizer: `scripts/10_finalize_ground_truth_review.py`.

Audit query set đạt các kiểm tra cấu trúc: 100 unique query ID, 100 unique URL, 100 unique
source product, không thiếu product trong snapshot, không lệch category và toàn bộ query đã
approved. q0056 đã được thay bằng URL ngoài catalog do người dùng cung cấp; kiểm tra trực quan
xác nhận đúng áo gile xám có cúc vàng của product 1730. Run sau sửa đưa product 1730 từ
missing lên rank 1.

Run testcase hiện hành: `image-human-top5-rule20-20260822-164228`, 100/100 query thành
công và 2.000 result rows. Exact Hit@1 đạt 0,980; Exact Hit@5 đạt 0,990; Exact Hit@10 và
Exact Hit@20 đều đạt 1,000. Report sử dụng Top 5 đã review và rule bảo thủ cho rank 6-20.

## 3. Phân tích nguyên nhân gốc

### P0 — Không trả đủ `top_k` sản phẩm duy nhất

Luồng hiện tại trong `services/search/service.py` là:

1. `_search_image_points(..., limit=top_k)` lấy candidate theo vector;
2. `_image_per_crop_limit()` dùng `max(top_k, IMAGE_CANDIDATE_POOL_SIZE)`;
3. với một crop, `top_k=20` và `IMAGE_CANDIDATE_POOL_SIZE=20`, Qdrant chỉ trả 20 point;
4. `_best_score_by_product()` mới khử các point trùng `product_id`;
5. API cắt lại top 20 sản phẩm.

Kết quả thực tế:

| Kiểm tra | Kết quả |
|---|---:|
| Raw result rows | 831 |
| Sản phẩm/query trung bình | 8,31 |
| Query trả dưới 5 sản phẩm | 4/100 |
| Query trả dưới 10 sản phẩm | 75/100 |
| Query trả dưới 20 sản phẩm | 100/100 |

`Precision@K` trong script được tính bằng `hits / K`, không phải `hits / số kết quả thực
trả`. Do vậy underfill tạo trần giả cho Precision@10/20. Nó cũng trực tiếp làm thấp Recall
và mAP vì nhiều sản phẩm relevant không có cơ hội xuất hiện.

### P0 — Ground truth chưa đo đúng “visual similarity”

Ground truth có 2.529 dòng, trung bình 25,29 relevant/query, trong khi API chỉ trả trung
bình 8,31 sản phẩm. Phân bố grade là:

| Grade | Số dòng | Quy tắc hiện tại |
|---:|---:|---|
| 3 | 100 | Đúng sản phẩm nguồn |
| 2 | 723 | Cùng category và trùng ít nhất 2 trong color/material/gender |
| 1 | 1.706 | Cùng category nhưng không đạt grade 2 |

Script `08_generate_balanced_testcases.py` tự đánh dấu các dòng này là `approved` và chỉ
lấy tối đa 30 sản phẩm cùng category. `05_compute_metrics.py` đang dùng
`relevance_threshold=1`, tức toàn bộ grade 1 cũng là relevant. Các vấn đề kéo theo:

- sản phẩm nhìn khác nhưng cùng category được coi là đúng;
- sản phẩm nhìn giống nhưng khác category bị coi là sai;
- Recall/mAP bị phạt vì hệ thống không trả đủ hàng chục sản phẩm cùng category;
- breakdown category có nhóm chỉ 1 query nên dao động không có ý nghĩa thống kê;
- NDCG có thể cao vì exact product grade 3 đứng đầu dù phần còn lại chưa thật sự tốt.

### P1 — Ảnh nhiều vật thể và góc chụp lifestyle

`YOLO_ENABLED=false` làm crop service dùng toàn ảnh. Với ảnh người mẫu có cả áo và quần,
vector có thể ưu tiên vật thể lớn hoặc nổi bật hơn sản phẩm nguồn. q0005 là ví dụ: sản phẩm
quần trong cùng outfit đứng rank 1, sản phẩm kỳ vọng đứng rank 2 với điểm bằng nhau.

Không nên bật hard category filter ngay. Detector có thể đoán sai và loại sản phẩm đúng.
Ban đầu cần giữ full image, thêm crop như một tín hiệu và dùng category detection để boost
mềm.

### P1 — Gộp điểm theo sản phẩm còn quá đơn giản

Hiện một sản phẩm được chấm bằng điểm cao nhất trong mọi image point. Cách `max score` dễ
bị một ảnh phụ nhiễu chi phối và không thưởng cho sản phẩm có nhiều góc chụp cùng khớp.
Đồng thời mỗi crop được truy vấn độc lập nhưng chưa có cơ chế product-level group/refill.

### P1 — Pure image search gần như chỉ dựa vào vector

`_boost_image_results()` chỉ tận dụng category/color khi request đã có filter rõ ràng. Với
bộ eval chỉ gửi ảnh, không có filter, nên ranking chủ yếu là cosine similarity. Khi YOLO
tắt, `_rank_points_by_detected_category()` cũng không có tín hiệu category đáng tin để
boost. Các case kiểu q0029 — áo/vest tối màu, form phổ biến — vì vậy dễ lẫn giữa nhiều sản
phẩm gần giống.

### P2 — Thiết kế query set còn leakage và chưa cân bằng

- 34 easy là ảnh catalog `DETAIL_1`, phù hợp smoke test nhưng lạc quan hơn production;
- medium/hard chỉ thay góc chụp, chưa bao phủ crop, nền phức tạp, ánh sáng kém, screenshot,
  che khuất và nhiều vật thể theo tỷ lệ có kiểm soát;
- một số category chỉ có 1 query, trong khi một số nhóm có 10–11 query;
- chưa tách rõ bài toán “tìm đúng SKU” và “tìm sản phẩm tương tự”.

### P2 — Khả năng quan sát runtime chưa đủ cho A/B

Run đã dùng đúng Bedrock và không có lỗi, nhưng report cần tự ghi thêm collection/version,
candidate count trước và sau dedupe, crop count, provider/model, latency embedding/Qdrant
và lý do fallback. Nếu thiếu các trường này, một thay đổi cấu hình có thể bị hiểu nhầm là
cải thiện model.

## 4. Luồng mục tiêu

```text
Ảnh query
  -> kiểm tra/chuẩn hóa ảnh
  -> full image + user crop hoặc detector crop
  -> Bedrock image embedding
  -> Qdrant overfetch theo từng crop
  -> gom point theo product_id
  -> aggregate score + category agreement mềm
  -> dedupe và refill cho đủ unique top_k
  -> product-level rerank (nếu A/B đạt gate)
  -> trả kết quả + diagnostic an toàn
```

Không sử dụng category/product metadata của chính query trong eval để boost vì đó là data
leakage. Category dùng lúc chạy thật phải được suy ra từ ảnh, user crop hoặc filter người
dùng gửi rõ ràng.

## 5. Kế hoạch triển khai

### Giai đoạn 0 — Sửa evaluation contract và khóa baseline (1–2 ngày)

- [ ] Giữ nguyên run `image-20260822-131404` làm baseline trước thay đổi.
- [x] Tách hai task và hai nhóm metric:
  - exact product retrieval: Exact Hit/Recall@1, @5, @10 và exact MRR;
  - similar product retrieval: graded NDCG@5/10/20, Recall@K và mAP.
- [x] Thêm `returned_count`, `unique_product_count`, `fulfillment@K` và
  `underfill_rate@K`; không để Precision@K che mất lỗi trả thiếu kết quả.
- [ ] Không coi `review_status=approved` nếu nhãn chỉ do rule sinh ra. Đổi thành
  `generated` hoặc `pending_review`.
- [x] Tạo review queue từ exact product và retrieval top 20, mọi dòng mặc định `pending`.
- [ ] Review thủ công theo hình ảnh với grade 0–3; không dùng grade gợi ý làm nhãn cuối.
- [ ] Review chéo ít nhất 20% query và báo agreement; mọi query phải có exact product grade
  3 nếu ảnh thật sự thuộc SKU đó.
- [ ] Báo metric cho cả threshold `>=2` và graded NDCG; grade 1 chỉ dùng nếu định nghĩa và
  review xác nhận rõ.
- [ ] Cân bằng category hoặc chỉ công bố breakdown khi có ít nhất 5 query/category.
- [ ] Tạo split `catalog-self-match`, `alternate-view` và `customer-like`; không gộp chúng
  thành một con số duy nhất.

Files dự kiến:

- `evals/search_evaluation/image/scripts/05_compute_metrics.py`;
- `evals/search_evaluation/image/scripts/08_generate_balanced_testcases.py`;
- `evals/search_evaluation/image/scripts/09_build_ground_truth_review.py`;
- `evals/search_evaluation/image/scripts/10_finalize_ground_truth_review.py`;
- `evals/search_evaluation/image/data/ground_truth_image_candidates.csv`;
- `evals/search_evaluation/image/data/ground_truth_image.csv`;
- `evals/search_evaluation/image/README.md`.

### Giai đoạn 1 — Overfetch, product grouping và refill (1–2 ngày)

- [x] Thêm cấu hình `IMAGE_PRODUCT_OVERFETCH_FACTOR`, mặc định `4`.
- [x] Lấy ít nhất `max(top_k * factor, IMAGE_CANDIDATE_POOL_SIZE)` point, trong giới hạn
  cap an toàn; với `top_k=20`, thử 80 point thay vì 20.
- [x] Dedupe theo `product_id`, nếu chưa đủ `top_k` thì tăng candidate limit theo cấp số
  nhân cho tới khi đủ hoặc chạm cap/collection đã cạn.
- [ ] Nếu Qdrant version hỗ trợ group-by ổn định, A/B group theo `product_id` với phương án
  overfetch phía service; chỉ chọn sau khi so latency và recall.
- [x] Luôn trả đúng `min(top_k, số sản phẩm hợp lệ trong catalog/filter)` unique products.
- [x] Ghi log initial/final limit, `raw_point_count`, `unique_product_count` và `refill_rounds`.
- [x] Thêm unit test cho nhiều vector cùng product và full run yêu cầu 20 unique
  products.

Files dự kiến:

- `service-ai/src/ecommerce_search_assistant/services/search/service.py`;
- `service-ai/src/ecommerce_search_assistant/core/config.py`;
- `service-ai/.env.example`;
- `service-ai/tests/unit/test_search_scoring.py`.

Đây là thay đổi P0 đầu tiên vì nó sửa đúng lỗi chức năng, không phụ thuộc đánh giá chủ quan
về model.

### Giai đoạn 2 — Crop và xử lý ảnh nhiều vật thể (2–4 ngày)

- [ ] Giữ full image như một candidate crop để không mất ngữ cảnh.
- [ ] Nếu người dùng crop thủ công, ưu tiên crop đó.
- [ ] Bật detector sau feature flag cho A/B; tối đa 3 crop có confidence/diện tích hợp lý.
- [ ] Dùng category detector làm soft boost, chưa hard filter cho đến khi đo false-negative.
- [ ] Fusion điểm giữa full image và crop; giảm trọng số crop quá nhỏ hoặc confidence thấp.
- [ ] Tạo regression set riêng cho outfit nhiều vật thể, gồm q0005 và ảnh có áo + quần.
- [ ] Khi có nhiều vật thể hợp lệ mà user chưa crop, UI/API nên cho chọn vùng muốn tìm.

Gate riêng của giai đoạn này: exact Hit@5 trên tập multi-object tăng mà exact Hit@5 trên
tập single-object không giảm quá 1 điểm phần trăm.

### Giai đoạn 3 — Product-level scoring và rerank nhẹ (3–5 ngày)

- [ ] A/B các hàm aggregate thay cho `max` thuần:
  - `max_score` làm baseline;
  - weighted top-2 image scores;
  - crop coverage và category agreement;
  - phạt nhẹ khi chỉ một ảnh phụ bất thường khớp.
- [ ] Chuẩn hóa contribution để sản phẩm có nhiều ảnh không tự động được lợi hơn.
- [ ] Thử category/color/material visual signal ở dạng soft rerank; không đọc metadata ẩn
  của query test.
- [ ] Chỉ thêm reranker model nếu phương án rule/fusion chưa đạt gate và chi phí/latency
  chấp nhận được.
- [ ] Lưu per-query delta và kiểm tra riêng q0029, q0056 thay vì chỉ nhìn aggregate.

### Giai đoạn 4 — Cải thiện index và dữ liệu ảnh (2–4 ngày)

- [ ] Audit mỗi image point có `product_id`, `category`, `image_type`, URL và index version.
- [ ] Loại ảnh hỏng, thumbnail quá nhỏ, ảnh không chứa sản phẩm hoặc ảnh trùng byte/hash.
- [ ] Giữ số view hợp lý trên mỗi product để category có nhiều ảnh không lấn candidate pool.
- [ ] Gắn image type và quality score để scoring có thể giảm trọng số ảnh phụ chất lượng kém.
- [ ] Version collection và lưu manifest model/preprocessing/checksum.
- [ ] Chỉ re-embed khi đổi model hoặc preprocessing. Việc chuyển transport sang Bedrock nhưng
  vẫn dùng `cohere.embed-v4:0` không tự động yêu cầu reindex; phải kiểm chứng vector parity
  trước khi quyết định.

### Giai đoạn 5 — Vận hành, lỗi và chi phí (1–2 ngày)

- [ ] Readiness/log ghi rõ embedding provider, model và collection đang dùng nhưng không ghi
  credential.
- [ ] Map lỗi upstream 429/timeout thành mã degraded phù hợp, retry có backoff và jitter.
- [ ] Eval runner hỗ trợ resume/retry, không trộn partial run vào report hợp lệ.
- [ ] Đo p50/p95 cho tải ảnh, embedding, Qdrant, rerank và end-to-end.
- [ ] Theo dõi request error rate, underfill rate, crop fallback rate và chi phí/query.
- [ ] Docker Compose không được hard-code provider đè cấu hình `.env`; thêm config regression
  test hoặc startup assertion cho Bedrock.

## 6. Thứ tự thí nghiệm

Mỗi thí nghiệm dùng cùng query split, ground truth version, Qdrant snapshot và Bedrock model.
Chỉ thay một nhóm biến mỗi lần.

| Run | Thay đổi | Mục đích |
|---|---|---|
| A0 | Baseline hiện tại | Mốc so sánh |
| A1 | Overfetch 2x | Đo unique coverage/latency |
| A2 | Overfetch 4x + refill | Chọn candidate policy |
| B1 | A2 + full image/crop fusion | Đo multi-object |
| B2 | B1 + soft category boost | Đo category confusion |
| C1 | B tốt nhất + weighted top-2 aggregate | Đo product scoring |
| C2 | C1 + reranker nếu cần | Chỉ giữ nếu quality/cost đạt gate |

Mỗi run phải lưu raw results, config snapshot, commit SHA, provider/model, collection version,
latency và aggregate/per-query metrics. Không chọn phương án chỉ dựa trên một metric.

## 7. Quality gate đề xuất

Sau Giai đoạn 0 cần rebaseline vì ground truth thay đổi. Các gate dưới đây là mục tiêu ban
đầu, sau đó khóa lại trước khi tối ưu model.

| Nhóm | Gate |
|---|---:|
| HTTP success | >= 99% |
| Unique fulfillment@5 | 100% nếu catalog/filter có đủ sản phẩm |
| Unique fulfillment@20 | >= 99% nếu catalog/filter có đủ sản phẩm |
| Exact Hit@1 toàn bộ | >= 0,970, không thấp hơn baseline |
| Exact Hit@5 toàn bộ | >= 0,990 |
| Exact Hit@5 medium | >= 0,970 |
| Exact Hit@5 hard | >= 0,970 |
| Graded NDCG@5 sau human review | >= 0,930 |
| Similar-product mAP | tăng ít nhất 20% tương đối so với baseline mới |
| Single-object regression | không giảm quá 1 điểm phần trăm |
| p95 latency | không tăng quá 20% so với baseline đã đo |
| Error/degraded rate | < 1% |

Precision@K không dùng làm gate duy nhất vì số relevant có thể nhỏ hơn K. Với bài toán
exact product, Hit@K/MRR phù hợp hơn; với bài toán sản phẩm tương tự, graded NDCG và human
judgment phù hợp hơn.

## 8. Test bắt buộc

- [x] Unit: candidate limit tăng theo `top_k` và overfetch factor.
- [x] Unit: nhiều point cùng `product_id` vẫn trả đủ K sản phẩm duy nhất.
- [x] Unit: refill dừng đúng khi đủ K, chạm cap hoặc Qdrant cạn.
- [ ] Unit: crop fallback luôn giữ full image.
- [ ] Unit: soft category boost không loại candidate khác category.
- [x] Full eval: collection 1.000 sản phẩm trả 20 unique products cho 100/100 query.
- [ ] Regression: q0005, q0029 và q0056.
- [ ] Eval: exact, similarity, difficulty, category và multi-object split.
- [ ] Config: container khởi động với `EMBEDDING_PROVIDER=bedrock` khi `.env` chọn Bedrock.

## 9. Rủi ro và rollback

- Overfetch tăng Qdrant latency: giới hạn cap, đo p95 và rollback factor qua env.
- Detector crop sai: feature flag, luôn giữ full image, category chỉ boost mềm.
- Human ground truth không nhất quán: hướng dẫn grade bằng ví dụ và review chéo.
- Reranker tăng chi phí/latency: mặc định tắt, chỉ bật nếu A/B vượt quality gate.
- Reindex sai model/version: tạo collection mới, smoke test rồi đổi alias; giữ collection cũ
  đến khi run đầy đủ đạt gate.

## 10. Definition of done

- [ ] Evaluation contract tách exact retrieval và visual similarity, có ground truth đã review.
- [x] API trả đủ unique `top_k` khi catalog/filter có đủ sản phẩm.
- [x] 100 query chạy không lỗi và report không chứa partial run.
- [ ] Exact Hit@1 không regression; exact Hit@5, NDCG@5 và mAP đạt gate đã khóa.
- [ ] Multi-object có crop/fusion được kiểm chứng bằng regression set.
- [ ] Provider/model/collection/candidate diagnostics và latency có trong run summary.
- [ ] Unit, integration và full evaluation đều đạt trong cùng một phiên bản cấu hình.
- [ ] Có feature flag và phương án rollback cho overfetch, crop và rerank.

## 11. Lệnh chạy lại baseline

Đọc tham số chính xác từ `evals/search_evaluation/image/README.md`; mỗi run phải dùng run ID
và file output mới, không ghi đè artifact baseline. Luồng tối thiểu là:

```powershell
cd C:\A\DACN_HK252

python evals/search_evaluation/image/scripts/04_run_search.py `
  --base-url http://localhost:8000 `
  --top-k 20 `
  --run-id "image-<timestamp>" `
  --output-csv "evals/search_evaluation/image/reports/search_results_image_<timestamp>.csv"

python evals/search_evaluation/image/scripts/05_compute_metrics.py `
  --results-csv "evals/search_evaluation/image/reports/search_results_image_<timestamp>.csv" `
  --output-json "evals/search_evaluation/image/reports/metrics_image_<timestamp>.json" `
  --output-csv "evals/search_evaluation/image/reports/metrics_image_<timestamp>.csv" `
  --k-values 5,10,20
```

Trước khi dùng các lệnh này làm automation, chạy `--help` để đối chiếu tên flag với phiên
bản script hiện tại.
