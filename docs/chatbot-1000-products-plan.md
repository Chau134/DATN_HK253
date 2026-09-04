# Kế hoạch cải thiện chatbot trên danh mục 1.000 sản phẩm

## Master-80-v2 và kế hoạch nghiệm thu A–D (26/08/2026)

Mười hai ca critical đã được đưa vào một bộ cố định gồm 80 câu, thay vì cộng riêng thành 92 câu.
Bộ mới giữ nguyên mọi phiên nhiều lượt và bỏ 12 ca cũ một lượt theo quota/seed cố định, không chọn
dựa trên điểm số trước đó.

Hiện còn 39 dòng ground truth cần duyệt rõ reference/evidence; 41 dòng cũ đã được duyệt. Đây là bước
duyệt đáp án tham chiếu và bằng chứng, không phải yêu cầu viết lại query. Sau khi khóa ground truth,
chạy A = LLM không RAG/memory; B = RAG không memory; C = RAG + memory, rerank tắt; D = RAG +
memory, rerank bật. A/B cô lập từng lượt, C/D giữ thứ tự phiên. Kết quả A--D được đưa vào báo cáo sau
khi ground truth được khóa, mỗi cấu hình chạy đủ 80 câu và các hard gate tự động được tổng hợp.

## 1. Mục tiêu và cách đọc kết quả

Tài liệu này ghi nhận kết quả kiểm định ngày 26/08/2026 và kế hoạch cải thiện chatbot cho bốn nhóm thông tin nhạy cảm: giá, tồn kho theo size, sản phẩm không tồn tại và chính sách không có căn cứ.

Hai lớp kiểm thử phải được hiểu tách biệt:

- **Kết quả chẩn đoán trước P0**: framework khi đó đạt 7/7, còn AI pre-review của 12 ca critical chỉ đề xuất 2/12 ca đạt.
- **Kết quả hiện tại sau P0**: automatic scorer đối chiếu response với context/evidence và đạt 12/12 hard gate.

Kết quả framework không tự chứng minh chatbot trả lời đúng; kết luận 12/12 dựa trên runtime response, evaluation trace, context/evidence và automatic critical scorer.

## 2. Có cần review lại query không?

**Không cần review lại toàn bộ 12 query.** Các câu đều tự nhiên, rõ ý và phù hợp mục tiêu kiểm thử. Tên và `source_product_id` đã khớp `product_snapshot.csv`:

| Sản phẩm | Product ID | Đối chiếu |
|---|---:|---|
| Bodysuit màu đen cổ tim gọng nâng phối tương phản | 1035 | Khớp, active |
| Quần dài ống suông màu trắng ngà vải piqué thắt lưng tương phản | 1903 | Khớp, active |
| Đầm sơ mi mini màu cát cotton kèm thắt lưng xẻ hông | 672 | Khớp, active |
| Đầm mini phồng màu đen gấu bo chun | 686 | Khớp, active |
| Quần dài ống rộng màu xanh dương cạp cao vạt chồng | 1823 | Khớp, active |

Qdrant đang dùng đúng collection `product_text_vectors_cohere_embed_v4_1536_metadata_v4_1000_products` với 1.000 điểm. Lỗi truy hồi ID 672 và 686 không phải do query sai hoặc collection chỉ có 100 sản phẩm.

Người review chỉ cần quyết định hai quy tắc nghiệp vụ:

1. Nội dung trong `shop_knowledge.py` có đúng chính sách chính thức của Mystery Closet không.
2. Với sản phẩm không tồn tại, chatbot phải từ chối hoàn toàn hay được phép từ chối rồi đề xuất sản phẩm gần giống.

Nếu cho phép đề xuất, câu trả lời vẫn phải nói rõ sản phẩm yêu cầu không tồn tại trước; không được trình bày nearest neighbor như sản phẩm người dùng hỏi.

Quyết định nghiệp vụ đã được xác nhận ngày 26/08/2026:

- `shop_knowledge.py` là nguồn chính sách chính thức khi nội dung đọc đúng thông tin đã công bố trong footer.
- Khi sản phẩm không tồn tại, chatbot phải từ chối/xác nhận không tìm thấy trước, sau đó mới được gợi ý sản phẩm tương tự.

## 3. Kết quả chẩn đoán 12 ca critical trước P0

| Nhóm | Số ca | AI pre-review đạt | Hiện tượng |
|---|---:|---:|---|
| Giá | 4 | 0 | Có context giá nhưng reply chỉ liệt kê sản phẩm |
| Tồn kho | 4 | 0 | Có variant và tồn kho nhưng reply không xác nhận còn/hết |
| Sản phẩm không tồn tại | 2 | 0 | Trả sản phẩm gần giống thay vì từ chối |
| Chính sách | 2 | 2 | Không chấp nhận cam kết giả nhưng chưa nói “không” trực tiếp |
| **Tổng** | **12** | **2** | **Hard gate không đạt** |

| Case | Kết quả quan sát | Nguyên nhân | Hành vi cần đạt |
|---|---|---|---|
| critical-price-001 | Đúng ID 1035; context có 579.000 VND nhưng reply không có giá | Thiếu nhánh price | Trả 579.000 VND; có thể kèm giá gốc 599.000 VND |
| critical-price-002 | Đúng ID 1903; context có 779.000 VND nhưng reply không có giá | Thiếu nhánh price | Trả 779.000 VND; có thể kèm giá gốc 799.000 VND |
| critical-price-003 | Không lấy ID 672; trả 530, 318, 664 | Rewrite/filter sai màu “cát”; thiếu exact-title lookup | Resolve ID 672 trước semantic search, rồi trả giá từ context |
| critical-price-004 | Không lấy ID 686; trả 621, 382, 360 | Rewrite sai “gấu bo chun”, thêm `tshirt style`; thiếu exact lookup | Resolve ID 686 và trả giá từ context |
| critical-stock-001 | Đúng ID 1035; size M còn 50 nhưng reply không nói tồn kho | Thiếu nhánh availability | Xác nhận size M còn hàng |
| critical-stock-002 | Đúng ID 1903; size L còn 50 nhưng reply không nói tồn kho | Thiếu nhánh availability | Xác nhận size L còn hàng |
| critical-stock-003 | Đúng ID 1823; size XS còn 50 nhưng reply không nói tồn kho | Thiếu nhánh availability; recovery được dùng | Xác nhận size XS và không bỏ size khi recovery |
| critical-stock-004 | Không lấy ID 686; không resolve variant S | Exact lookup thất bại; recovery trả sản phẩm khác | Resolve ID 686; trả trạng thái size S hoặc nói không có variant |
| critical-product-001 | Trả ID 10 cho “Áo khoác Sao Hỏa 2099” | Vector search luôn trả nearest neighbor; thiếu no-match gate | Nói không tìm thấy; chỉ đề xuất gần giống sau lời từ chối |
| critical-product-002 | Trả 677, 332, 485 cho MC-999999 | Không ưu tiên exact code; thiếu no-match gate | Xác nhận không có mã MC-999999 |
| critical-policy-001 | Trả chính sách 30/60 ngày | An toàn nhưng thiếu yes/no trực tiếp | Mở đầu “Không”, sau đó nêu chính sách có căn cứ |
| critical-policy-002 | Trả chính sách đổi trả 7 ngày | An toàn nhưng thiếu yes/no trực tiếp | Mở đầu “Không”, sau đó nêu chính sách có căn cứ |

## 4. Nguyên nhân gốc

### 4.1. Intent quá rộng

Giá, tồn kho, mã sản phẩm và tìm kiếm đều bị gán `intent=search_product`. Cần phân biệt ít nhất `product_price`, `product_availability`, `exact_product_lookup`, `product_search` và `shop_policy`. Nếu không biết thuộc tính đích, reply generator mặc định biến câu hỏi thành yêu cầu gợi ý sản phẩm.

### 4.2. Structured reply trả quá sớm

Trong `service-ai/src/ecommerce_search_assistant/services/assistant/workflow.py`, `_generate_reply` gọi `_structured_catalog_reply` trước LLM. Hàm này chỉ xử lý màu, chất liệu, giới tính và danh mục; chưa xử lý giá/tồn kho nhưng cuối hàm vẫn trả “Gợi ý các sản phẩm ...”. Vì vậy context đúng không được dùng và LLM không có cơ hội trả lời.

### 4.3. Query rewrite làm biến dạng entity

Trace cho thấy “gấu bo chun” thành nội dung có `bear`, `bo chun pattern`, `tshirt style`; “màu cát” bị suy ra filter `pink` và `cream`. Query gốc không sai. Rewrite phải bảo toàn nguyên văn tên/mã sản phẩm và chỉ phân tích phần còn lại.

### 4.4. Thiếu exact-match và confidence/no-match gate

Tên đầy đủ và mã sản phẩm vẫn đi thẳng vào semantic top-k. Qdrant luôn trả nearest neighbor kể cả khi entity không tồn tại. Hệ thống thiếu exact code lookup, normalized-title lookup, ngưỡng confidence, kiểm tra token coverage và trạng thái `no_match`.

### 4.5. Recovery có thể làm mất ràng buộc cứng

Với price/stock của exact product, title, product ID và size là hard constraints; không được nới như filter khám phá sản phẩm. Hai ca stock đã xuất hiện `search_recovery_used`.

### 4.6. Scorer policy có false negative

Scorer chỉ nhận một số cụm từ từ chối. Hai reply policy bác bỏ cam kết giả bằng chính sách đúng nhưng không có từ “không”, nên automatic result vẫn fail. Scorer phải phân biệt: khẳng định cam kết giả (fail), từ chối trực tiếp (pass), và grounded correction thiếu phủ định trực tiếp (pass kèm `directness_warning`).

## 5. Kế hoạch cải thiện

### P0 — Sửa hard gate

1. **Thêm answer target/intent:** nhận diện riêng price, availability, exact product và policy.
2. **Resolve exact product trước semantic search:** code/ID → normalized title → lexical match → semantic fallback.
3. **Structured price reply:** lấy `effective_price` của đúng target; không có context thì từ chối, không lấy giá của sản phẩm khác.
4. **Structured stock reply:** resolve đúng `unified_size`/`option_value`; dùng `available`, `active`, `inventory_count`; không suy tồn kho size từ `total_stock`.
5. **No-match/refusal gate:** exact entity không resolve hoặc semantic score thấp thì nói không tìm thấy; suggestion chỉ là tùy chọn được gắn nhãn rõ.
6. **Policy direct answer:** dùng mẫu “Không, shop không có cam kết đó. Chính sách hiện có là ...”; phần policy chỉ lấy từ nguồn đã duyệt.

Tiêu chí P0:

- 4/4 price query nhận diện đúng và trả đúng giá target.
- 4/4 stock query giữ đúng size và trả đúng trạng thái variant.
- 2/2 mã/tên giả đi vào `no_match`.
- 2/2 policy phủ định trực tiếp cam kết giả.

### P1 — Cải thiện retrieval/query understanding

1. Trích entity span trước LLM rewrite và đánh dấu không được sửa/dịch.
2. So sánh token coverage query gốc với rewritten query; nếu mất token quan trọng thì dùng query gốc/hybrid query.
3. Thêm regression vocabulary cho `màu cát`, `gấu bo chun`, `piqué`, `vạt chồng`, `gọng nâng`, `sơ mi mini`; không dịch “gấu” thành “bear” trong ngữ cảnh may mặc.
4. Không bỏ product identity hoặc size khi search recovery cho exact product.
5. Hiệu chỉnh confidence/no-match bằng pilot gồm exact match, paraphrase và negative product; ưu tiên precision để tránh giới thiệu sai sản phẩm.

### P2 — Mở rộng framework và khả năng tái lập

Giữ 7 test hiện có và thêm tối thiểu:

1. Price reply dùng đúng `effective_price` của target.
2. Stock reply dùng đúng variant/size, không thay bằng `total_stock`.
3. Exact-title resolution cho ID 672 và 686.
4. Exact code không tồn tại trả `no_match`.
5. Nearest neighbor không được coi là exact product.
6. Rewrite bảo toàn entity span.
7. Recovery không bỏ size/product identity.
8. Policy contradiction bắt buộc phủ định trực tiếp.
9. Policy scorer nhận grounded correction và phát warning nếu thiếu phủ định.
10. End-to-end 12 critical cases chạy trên full-stack.

Báo cáo phải tách riêng framework/unit tests, metric RAG và automatic critical gates. Không dùng “7/7 test đạt” thay cho “chatbot đạt 12 hard gate”.

## 6. Chuẩn hóa môi trường kiểm thử

Khi service-ai chạy Docker standalone và Spring Boot chạy trên host:

```env
SPRINGBOOT_BASE_URL=http://host.docker.internal:8080
```

Không dùng `localhost:8080` từ trong container. Trước mỗi eval phải xác nhận:

- `/health/ready` của service-ai trả 200.
- Spring product-context endpoint truy cập được từ service-ai.
- Qdrant collection có đúng 1.000 points.
- `retrieved_context` không rỗng cho positive product cases.
- Metadata có commit SHA, execution ID, endpoint và collection.

## 7. Thứ tự triển khai và điều kiện hoàn thành

Thứ tự:

1. Viết regression tests cho 12 lỗi hiện tại.
2. Thêm answer target và exact product resolver.
3. Bổ sung reply cho price, availability và no-match.
4. Sửa rewrite và hard-constraint recovery.
5. Cập nhật policy scorer.
6. Chạy unit/integration tests và 12 ca full-stack.
7. Tổng hợp metric A--D và cập nhật kết luận vào chương đánh giá hệ thống.

Hoàn thành khi 12/12 request có trace hợp lệ; 4/4 giá đúng; 4/4 tồn kho đúng; 2/2 sản phẩm giả được từ chối; 2/2 policy phủ định cam kết giả; automatic scorer xác nhận 12/12 hard gate đạt; các metric retrieval/grounding khác không giảm ngoài ngưỡng đã thống nhất.

## 8. Artifact kiểm định

- `evals/conversational_ai_validation/data/critical_cases.csv`
- `evals/conversational_ai_validation/reports/critical_gate_responses.csv`
- `evals/conversational_ai_validation/reports/critical_gate_run_metadata.json`
- `evals/conversational_ai_validation/review/critical_gate_review.csv`
- `evals/conversational_ai_validation/review/critical_gate_ai_assessment.csv`
- `evals/conversational_ai_validation/reports/critical_gate_summary.json`

## 9. Implementation status (26/08/2026)

The implementation work in P0 and the exact-entity/hard-constraint parts of P1 is complete:

- Added explicit answer targets for price, availability, exact product lookup and shop policy.
- Added exact product ID/code and normalized-title resolution before semantic search.
- Preserved the original product entity before LLM rewrite; exact requests cannot be silently rebound to a nearest neighbor.
- Added deterministic price and variant-level stock replies from runtime context.
- Added a `no_match` response that refuses first and only then labels optional similar-product suggestions.
- Added direct policy denial followed by the official footer-aligned policy from `shop_knowledge.py`.
- Kept exact product identity and requested size as hard constraints during recovery.
- Updated the critical scorer to accept labeled suggestions only after refusal and to recognize grounded direct policy corrections.
- Configured standalone Docker access to Spring Boot through `host.docker.internal`; the full compose stack continues to use `spring-api`.

Verified results:

| Verification layer | Result | Meaning |
|---|---:|---|
| Entire `service-ai` test suite | 412/412 passed | No detected regression in the current service suite |
| Validation framework tests | 13/13 passed | Includes master-80 selection and critical applicability coverage |
| Runtime critical automatic scorer | 12/12 passed | 4 price, 4 stock, 2 missing-product and 2 unsupported-policy cases |
| Runtime HTTP/context trace | 12/12 valid | Every request returned HTTP 200 with `full_context` |
| Human critical review | 12/12 confirmed | Final critical hard gate passed |

The critical query set does not need to be rewritten and its 12 human decisions are complete.
The remaining review action concerns the reference/evidence ground truth in the consolidated
master-80 packet, not the wording of those 12 queries.
