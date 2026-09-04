# Conversational AI Evaluation Plan

Tài liệu này là bản nháp kế hoạch xây dựng bộ test đánh giá chatbot/RAG độc lập với
Search Evaluation. Khác với Search Evaluation, ground truth ở đây không phải danh sách
sản phẩm relevant, mà là câu trả lời tham chiếu (`reference_answer`) được xây dựng từ
nguồn tri thức của hệ thống. Hệ thống hiện tại kết hợp **product-RAG** cho catalog với route
`shop_knowledge` xác định cho thông tin footer/chính sách. Vì vậy `reference_answer` được viết
từ cả snapshot sản phẩm lẫn dữ liệu Mystery Closet đã công bố (xem mục 5).

## Bối cảnh hệ thống thực tế

Chatbot chạy trên hai service, eval cần bám đúng kiến trúc này:

- `service-ai` (FastAPI + LangGraph): sở hữu orchestration hội thoại, query understanding,
  retrieval (Qdrant vector search) và sinh câu trả lời bằng Bedrock GPT OSS theo cấu hình hiện tại;
  Gemini Embedding 2 trên Vertex AI chỉ tạo vector retrieval. Endpoint chính: `POST /assistant/chat`.
- `service-api-ecommerce` (Spring Boot): gateway mà frontend gọi (`POST /api/assistant/chat`),
  đồng thời là **source-of-truth** cho metadata + tồn kho sản phẩm; `service-ai` gọi ngược lại
  qua HTTP callback để lấy product context và kiểm tra availability.

Luồng: `React -> Spring Boot /api/assistant/chat -> service-ai /assistant/chat -> LangGraph
(Bedrock + Qdrant + batch product context từ Spring Boot) -> trả về product_ids + message`.

Điểm quan trọng cho eval:

- Chatbot có route xác định cho tên/địa chỉ shop, tổng quan catalog và các chính sách đã công bố;
  product-RAG vẫn xử lý thuộc tính sản phẩm, tư vấn/so sánh và follow-up nhiều lượt.
- Retrieved context (product_context) **không được API trả ra**, chỉ tồn tại nội bộ trong
  LangGraph state (xem mục 2.3, 2.4).
- Nếu Bedrock bị tắt hoặc không khả dụng, tầng LLM tụt về fallback rule-based (deterministic) —
  ảnh hưởng tới tính tái lập của eval.

## 1. Mục tiêu

- Đánh giá chất lượng trả lời của Conversational AI trong các tình huống tư vấn thương mại điện tử.
- Kiểm tra chatbot có trả lời đúng theo context sản phẩm được truy hồi hay không.
- Đo mức độ câu trả lời bám sát câu hỏi, đầy đủ thông tin, và không bịa ngoài nguồn tri thức.
- Kiểm tra chatbot tuân thủ guardrail: không bịa product_id/giá/tồn kho/khuyến mãi, và từ chối
  đúng cách với câu hỏi ngoài phạm vi (ví dụ chính sách chưa được hỗ trợ).
- Đánh giá chất lượng hội thoại nhiều lượt: nhớ filter, tham chiếu sản phẩm trước, follow-up tồn kho.
- Tạo bộ test có thể tái chạy để so sánh nhiều phiên bản prompt, retriever, LLM, context builder,
  hoặc reranker.

## 2. Metrics

### 2.1 Faithfulness

Đo mức độ câu trả lời của LLM được hỗ trợ bởi retrieved context.

Câu trả lời faithfulness cao khi:

- Các claim chính trong câu trả lời đều có bằng chứng trong context.
- Không thêm thông tin không có trong context.
- Không suy diễn quá mức từ metadata hoặc chính sách.
- Không trả lời sai khi context thiếu dữ liệu.

Ví dụ lỗi:

- Context nói sản phẩm màu đen, chatbot trả lời màu xanh.
- Context không có chính sách hoàn tiền, chatbot tự bịa điều kiện hoàn tiền.
- Context chỉ có giá hiện tại, chatbot tự nói đang giảm 50%.

### 2.2 Response Relevancy

Đo mức độ câu trả lời trực tiếp giải quyết câu hỏi người dùng.

Câu trả lời relevancy cao khi:

- Trả lời đúng ý định của câu hỏi.
- Không lan man sang thông tin không cần thiết.
- Có đủ chi tiết cần thiết cho người mua ra quyết định.
- Nếu không đủ dữ liệu, nói rõ thiếu thông tin thay vì trả lời vòng vo.

### 2.3 Context Precision

Đo tỷ lệ context được retriever đưa vào là thật sự hữu ích cho câu hỏi.

```text
Context Precision = relevant_context_chunks / retrieved_context_chunks
```

Metric này giúp phát hiện retriever lấy quá nhiều đoạn không liên quan, làm chatbot dễ nhiễu
hoặc tốn token.

> **Điều kiện tiên quyết (hiện chưa đáp ứng):** response của `POST /assistant/chat` chỉ trả
> `product_ids` (id + score + source), `filters`, `rewritten_query`, `warnings`. Retrieved
> context thực tế (`product_context` — metadata Spring Boot + availability dùng để grounding)
> chỉ tồn tại nội bộ trong `AssistantState`, **không được expose**. Do đó Context Precision
> chưa đo trực tiếp được từ API. Ba lựa chọn để bật metric này:
>
> - (a) thêm field debug/eval vào `AssistantChatResponse` để trả kèm retrieved context;
> - (b) tái dựng context bằng cách fetch lại các `product_ids` trả về từ Spring Boot;
> - (c) instrument LangGraph workflow để log `product_context` mỗi turn.
>
> Trước khi có một trong ba, dùng `product_ids` + score làm proxy: coi mỗi product trả về là
> một "context chunk" và gán nhãn relevance cho từng product.

### 2.4 Context Recall

Đo tỷ lệ thông tin cần thiết cho reference answer đã xuất hiện trong retrieved context.

```text
Context Recall = required_evidence_chunks_retrieved / required_evidence_chunks_total
```

Metric này giúp phát hiện retriever thiếu bằng chứng quan trọng, khiến LLM không thể trả lời
đúng dù prompt tốt.

> Lưu ý (giống 2.3): Context Recall cũng cần retrieved context đầy đủ. Với response API hiện tại,
> chỉ đo được recall ở mức product (product cần thiết có nằm trong `product_ids` trả về không),
> chưa đo được recall ở mức field/chunk (giá, màu, size, mô tả) cho tới khi expose được
> `product_context`.

## 3. Quy trình tổng quát

```text
Question
  -> Retrieved Context
  -> LLM Answer
  -> Ground Truth Answer / Reference Answer
  -> Faithfulness
  -> Response Relevancy
  -> Context Precision
  -> Context Recall
```

Điểm khác với Search Evaluation:

- Search Evaluation đánh giá danh sách sản phẩm trả về.
- Conversational AI Evaluation đánh giá câu trả lời của chatbot.
- Ground truth của Search là tập `relevant_product_id`.
- Ground truth của Conversational AI là `reference_answer` và `required_evidence`.
- Context Precision/Recall dùng nhãn relevance của context chunk, không dùng SQL product matching
  làm ground truth chính.

## 4. Cấu trúc thư mục đề xuất

```text
evals/conversational_ai_evaluation/
  README.md
  configs/
    evaluation.yaml
  data/
    product_snapshot.csv
    question_set.csv
    reference_answers.csv
    required_evidence.csv
    retrieved_contexts.csv
    llm_answers.csv
    judged_answers.csv
  reports/
    latest_summary.md
    metrics_by_category.csv
    metrics_by_question.csv
  scripts/
    common.py
    01_build_product_snapshot.py
    02_generate_questions.py
    03_create_reference_answers.py
    04_run_chatbot.py
    05_judge_answers.py
    06_compute_metrics.py
```

Ghi chú: hiện tại mới tạo plan, chưa có scripts/data/config. Khi hiện thực nên **mirror cấu trúc
đã build đầy đủ ở `evals/search_evaluation/text/`** (`common.py` chứa dataclass + IO helper,
các script đánh số `01..05`, `configs/*.yaml` viết bằng JSON hợp lệ để đọc bằng thư viện chuẩn,
`data/`, `reports/`). Khác biệt chính so với search eval: nguồn dữ liệu là `product_snapshot.csv`
(không có `knowledge_sources.csv` policy/FAQ), và cần thêm bước judge (`05_judge_answers.py`) vì
ground truth là câu trả lời chứ không phải danh sách product.

## 5. Nguồn tri thức

Bộ test RAG cần xác định rõ nguồn nào được xem là sự thật. Hệ thống hiện là product-RAG nên
nguồn tri thức gồm dữ liệu sản phẩm đã index và knowledge xác định từ footer/chính sách shop.

### 5.1 Nguồn thực tế đang có

Text embedding được dựng từ các trường sau (xem `services/embeddings/formatting.py`,
`build_product_embedding_text`):

- Tên sản phẩm: `title`, `title_vi`.
- `variant`, `description_vi`.
- `categories` (+ bản `_vi`), `brand`, `colors` (+ `_vi`), `sizes`, `gender`.
- `price`, `discounted_price`.
- Các trường search tiếng Việt dựng sẵn: `embedding_search_text_vi`, `search_keywords_vi`,
  `search_attributes_vi`, `search_use_cases_vi`.

Qdrant payload (xem `services/indexing/product.py`, `_product_payload`) lưu thêm:
`total_stock`, `available`, `is_active`, `updated_at`.

Lưu ý về source-of-truth: **giá và tồn kho realtime lấy từ Spring Boot callback**
(`get_products_by_ids`, `check_product_availability`), không phải từ Qdrant payload. Do đó
`reference_answer` liên quan tới giá/tồn kho phải version theo snapshot DB Spring Boot tại thời
điểm chạy eval, vì các giá trị này thay đổi theo thời gian.

Schema đề xuất cho snapshot sản phẩm (`product_snapshot.csv`) — dùng làm nguồn viết reference
answer và required evidence:

```csv
product_id,title,title_vi,variant,description_vi,category,category_vi,brand,colors,colors_vi,sizes,gender,price,discounted_price,total_stock,available,is_active,version,updated_at
```

Trong đó `version` là id snapshot để đảm bảo eval tái lập.

### 5.2 Chưa có trong hệ thống (future work)

Thông tin footer và chính sách chưa được vector hóa nhưng được phục vụ qua route deterministic
`shop_knowledge`: tên/địa chỉ/liên hệ, catalog overview, vận chuyển, đổi trả, thanh toán và bảo
hành. Promotion/coupon không được công bố và các tuyên bố như người nổi tiếng sử dụng hay cam
kết công dụng vẫn là `unanswerable`.

## 6. Xây dựng Question Set

### 6.1 Nhóm câu hỏi đề xuất

Các nhóm câu hỏi bám đúng năng lực thực tế của chatbot (product-RAG + follow-up nhiều lượt):

- Product factual QA: hỏi thuộc tính sản phẩm (màu, chất liệu, danh mục, giá).
- Product comparison: so sánh 2 hoặc nhiều sản phẩm.
- Product recommendation: tư vấn chọn sản phẩm theo nhu cầu.
- Follow-up tham chiếu sản phẩm: câu hỏi dùng ordinal ("cái thứ 2 thì sao") dựa trên
  `last_product_ids` của lượt trước — nhánh đã implement trong `workflow.py`
  (`_extract_ordinal_index` / `_resolve_referenced_product_ids`).
- Availability follow-up: hỏi tồn kho theo màu/size ("còn màu trắng không", "còn hàng không") —
  kích hoạt `_needs_availability_check` gọi Spring Boot `check_product_availability`.
- Filter refinement: tinh chỉnh filter dựa trên context trước ("rẻ hơn nữa", "màu đen thì sao") —
  nhánh `_is_filter_refinement` / `_contextual_filters`, merge vào `last_filters`.
- Image/hybrid chat: gửi ảnh (kèm/không kèm text) để tìm sản phẩm tương tự.
- Clarification: câu phụ thuộc lịch sử nhưng thiếu history, kỳ vọng chatbot hỏi lại thay vì đoán.
- Shop knowledge: tên/địa chỉ, catalog overview và chính sách đã công bố; kỳ vọng trả lời trực tiếp.
- Unanswerable/ngoài phạm vi: yêu cầu cam kết hoặc tuyên bố không có nguồn; kỳ vọng không bịa.

### 6.2 Quy mô bản đầu tiên

Test set tối thiểu (nhất quán với `docs/chatbot.md`) — 80 câu để chạy vòng đầu:

- 20 product recommendation.
- 20 product factual QA.
- 10 follow-up tham chiếu sản phẩm (ordinal).
- 10 filter refinement.
- 10 product comparison.
- 8 shop knowledge.
- 2 unanswerable/unsupported claim.

Khi mở rộng, có thể nâng lên 200 câu, giữ tỷ lệ tương tự và bổ sung thêm comparison + availability
follow-up. Nếu muốn bản nhỏ để chạy nhanh: mỗi nhóm tối thiểu 5 câu.

### 6.3 Cách sinh câu hỏi

Quy trình:

1. Chọn snapshot nguồn tri thức (sản phẩm đã index).
2. Random sampling sản phẩm theo seed cố định (có thể tái dùng `sample_products_for_queries`
   trong `evals/search_evaluation/text/scripts/common.py`).
3. Sinh câu hỏi bằng template.
4. Bổ sung câu hỏi thủ công giống người dùng thật.
5. Gắn category, expected answer type, và required source.
6. Review thủ công để loại câu mơ hồ ngoài ý định test.

Template product factual:

- `{product_name} có màu gì?`
- `{product_name} làm từ chất liệu gì?`
- `{product_name} phù hợp cho nam hay nữ?`
- `{product_name} thuộc danh mục nào?`
- `{product_name} giá bao nhiêu?`

Template recommendation:

- `Tôi cần {category} màu {color} để {usage}, có gợi ý nào không?`
- `Tôi muốn mua đồ {material} cho {gender}, nên chọn sản phẩm nào?`
- `Có sản phẩm nào giống phong cách {style} nhưng giá thấp hơn không?`

Template comparison:

- `So sánh {product_a} và {product_b}.`
- `{product_a} khác gì so với {product_b}?`
- `Sản phẩm nào phù hợp hơn để {usage}: {product_a} hay {product_b}?`

Template follow-up nhiều lượt (chạy trong cùng `session_id`, sau một lượt search trước đó):

- Ordinal reference: `cái thứ 2 thì sao?`, `mẫu đầu tiên còn không?`
- Availability follow-up: `còn màu trắng không?`, `size M còn hàng không?`
- Filter refinement: `rẻ hơn nữa có không?`, `màu đen thì sao?`

Template shop knowledge (kỳ vọng trả lời từ footer/chính sách/catalog thật):

- `Đơn hàng được giao trong bao lâu?`
- `Shop hiện tại có tên là gì? Cho tôi vị trí của shop được không?`
- `Shop hiện tại đang bán những loại sản phẩm nào?`

Template unanswerable (kỳ vọng chatbot không xác nhận điều không có nguồn):

- `Sản phẩm này có chắc chắn giúp tôi trông cao hơn không?`
- `{name} có được người nổi tiếng nào mặc chưa?`
- `Tôi có thể đổi trả sản phẩm trong mấy ngày?`
- `Thanh toán bằng phương thức nào?`
- `{product_name} có được người nổi tiếng nào mặc chưa?`
- `Sản phẩm này có chắc chắn giúp tôi trông cao hơn không?`
- `Shop có giao trong 10 phút không?`

Schema đề xuất:

```csv
question_id,session_id,turn_index,category,question,expected_answer_type,entity_ids,depends_on_history,difficulty,manual_status,notes
```

Trong đó:

- `session_id` + `turn_index`: các câu follow-up nhiều lượt dùng chung `session_id` và tăng
  `turn_index`; eval runner phải gửi đúng thứ tự để giữ context (xem mục 9).
- `depends_on_history`: `true` cho câu phụ thuộc lượt trước (ordinal, availability, filter
  refinement); dùng để tách nhóm khi tính metrics.
- `entity_ids`: `product_id` liên quan (để dựng reference answer và required evidence).

## 7. Xây dựng Reference Answer

Reference answer là câu trả lời chuẩn cho từng question, viết dựa trên nguồn tri thức.

Nguyên tắc:

- Chỉ dùng thông tin có trong knowledge sources.
- Viết ngắn gọn, đúng trọng tâm câu hỏi.
- Nếu nguồn thiếu thông tin, reference answer phải nói rõ chưa có dữ liệu.
- Nếu câu hỏi mơ hồ, reference answer nên thể hiện hành vi hỏi lại hoặc nêu giả định.
- Với recommendation, reference answer nên nêu lý do dựa trên metadata/chính sách.
- Với comparison, reference answer cần liệt kê điểm giống/khác quan trọng.

Schema đề xuất:

```csv
question_id,reference_answer,answer_must_include,answer_must_not_include,reference_source_ids,review_status,notes
```

Trong đó:

- `answer_must_include`: các ý bắt buộc cần có.
- `answer_must_not_include`: các claim không được nói, ví dụ cam kết sai chính sách.
- `reference_source_ids`: nguồn dùng để viết câu trả lời chuẩn.

## 8. Xây dựng Required Evidence

Required evidence là danh sách thông tin hoặc chunk bắt buộc phải được retrieved để LLM có cơ sở
trả lời đúng.

Schema đề xuất:

```csv
question_id,evidence_id,source_id,evidence_text,evidence_role,required_level,notes
```

Trong đó:

- `evidence_role`: `primary`, `supporting`, `constraint`.
- `required_level`: `must_have`, `nice_to_have`.

Ví dụ:

- Với câu hỏi giá sản phẩm, evidence `price` là `must_have`.
- Với câu hỏi đổi trả, policy đổi trả là `must_have`, FAQ phụ là `nice_to_have`.
- Với câu hỏi recommendation, category/color/material có thể là `primary`, mô tả style là `supporting`.

## 9. Chạy Chatbot và lưu kết quả

Eval gọi trực tiếp `service-ai POST /assistant/chat` (giàu tín hiệu hơn: `product_ids` kèm
score/source, `rewritten_query`, `filters`, `warnings`). Nếu muốn đánh giá sát end-user, có thể
gọi `service-api-ecommerce POST /api/assistant/chat` (trả product card đã resolve). RAG metrics
nên dùng endpoint `service-ai`.

Request schema thực (`schemas/chat.py` — `ChatRequest`, snake_case):

```json
{
  "session_id": "eval-conv-0001",
  "user_id": "eval-user",
  "message": "...",
  "image": null,
  "crop_box": null,
  "locale": "vi-VN"
}
```

Response schema thực (`schemas/assistant.py` — `AssistantChatResponse`, bỏ field null):

```json
{
  "session_id": "eval-conv-0001",
  "message": "...",
  "product_ids": [{"product_id": "...", "score": 0.0, "source": "text", "rerank_score": null}],
  "filters": {"category": "...", "brand": "...", "colors": [], "sizes": [], "min_price": null, "max_price": null, "gender": "...", "material": "..."},
  "rewritten_query": "...",
  "warnings": ["spring_boot_unavailable"]
}
```

Với mỗi turn:

1. Gọi `/assistant/chat` với đúng `session_id` của hội thoại.
2. Lưu `product_ids` (id + score + source) làm proxy cho retrieved context (xem mục 2.3).
3. Lưu `message` (câu trả lời cuối), `filters`, `rewritten_query`, `warnings`.
4. Lưu metadata run: model, prompt version, retriever version, top_k, temperature.

Hội thoại nhiều lượt: các turn trong cùng một hội thoại phải dùng **cùng `session_id`**
(là LangGraph thread_id) để giữ context (`last_product_ids`, `last_filters`) giữa các lượt.
Đây là khác biệt cốt lõi so với Search Evaluation, nơi mỗi query độc lập. Turn phải chạy tuần tự
theo đúng thứ tự để follow-up ("cái thứ 2 thì sao", "còn màu trắng không", "rẻ hơn nữa") hoạt động.

Schema turn result:

```csv
run_id,conversation_id,question_id,turn_index,session_id,message,product_ids_json,filters_json,rewritten_query,warnings,latency_ms,springboot_call_count,model,prompt_version,metadata_json
```

Yêu cầu tái lập:

- Đặt `GEMINI_TEMPERATURE=0` khi benchmark. Lưu ý: nếu thiếu `GEMINI_API_KEY`, hệ thống chạy
  fallback rule-based deterministic — hữu ích làm baseline rule-only nhưng phải ghi rõ trong run.
- Pin snapshot Qdrant (vector đã index) và snapshot DB Spring Boot (metadata + tồn kho), vì
  giá/availability là source-of-truth động từ Spring Boot.
- Lưu raw response để debug.
- Không trộn dữ liệu của nhiều snapshot trong cùng một run.
- Có `run_id` để so sánh nhiều phiên bản.
- Nếu turn có `warnings` chứa `spring_boot_unavailable`, ghi nhận để phân tích riêng: câu trả lời
  về giá/tồn kho lúc này phải nói dữ liệu realtime có thể chưa cập nhật, không được bịa.

## 10. Chấm điểm

Có 2 cách chấm điểm:

- LLM-as-a-judge: dùng model judge để chấm theo rubric.
- Human review: người kiểm tra chấm một phần hoặc toàn bộ câu hỏi.

Khuyến nghị:

- Dùng LLM-as-a-judge cho toàn bộ bộ test.
- Human review ít nhất 20% câu hỏi ở vòng đầu.
- Human review toàn bộ các câu hỏi fail nghiêm trọng hoặc câu hỏi policy.

### 10.1 Faithfulness Rubric

Thang điểm `0-1` hoặc `0-5`.

Đề xuất `0-5`:

- `5`: mọi claim quan trọng đều được context hỗ trợ.
- `4`: có suy diễn nhẹ nhưng không làm sai ý.
- `3`: phần lớn đúng, có một vài claim thiếu bằng chứng.
- `2`: có claim quan trọng không được context hỗ trợ.
- `1`: nhiều claim sai hoặc bịa.
- `0`: trả lời trái context hoặc hoàn toàn không có căn cứ.

### 10.2 Response Relevancy Rubric

Thang điểm `0-5`:

- `5`: trả lời trực tiếp, đầy đủ, đúng trọng tâm.
- `4`: đúng trọng tâm nhưng thiếu chi tiết nhỏ.
- `3`: trả lời một phần, còn chung chung.
- `2`: có liên quan nhưng không giải quyết ý chính.
- `1`: gần như lạc đề.
- `0`: không trả lời câu hỏi.

### 10.3 Guardrail / Hallucination Compliance

Ngoài điểm số, chấm pass/fail theo các rule guardrail đã được cài trong `_assistant_reply_prompt`
(`services/gemini/service.py`). Câu trả lời **fail guardrail** nếu vi phạm bất kỳ điều nào:

- Bịa `product_id` không có trong `product_ids` trả về.
- Tự khẳng định còn hàng / hết hàng, giá cuối, hoặc mức giảm giá khi context không có.
- Lộ thuật ngữ kỹ thuật (RAG, embedding, vector, API) cho người dùng.
- Với câu hỏi `shop_knowledge`: từ chối dù thông tin đã công bố, hoặc tự thêm danh mục catalog.
- Với câu hỏi `unanswerable`: bịa cam kết/công dụng/người nổi tiếng thay vì nói không có căn cứ.
- Khi `warnings` có `spring_boot_unavailable`: khẳng định giá/tồn kho realtime thay vì nói dữ liệu
  có thể chưa cập nhật.

Đây là nhóm rule quan trọng nhất cho eval product-RAG, vì hallucination về giá/tồn kho gây rủi ro
kinh doanh trực tiếp.

### 10.4 Context Precision Rubric

> Điều kiện tiên quyết: chỉ tính được khi retrieved context đã được expose (xem mục 2.3). Trước
> đó dùng `product_ids` + score làm proxy context chunk.

Với mỗi retrieved context chunk, gán nhãn:

- `relevant`: cần thiết hoặc hữu ích để trả lời câu hỏi.
- `partially_relevant`: có liên quan nhưng không đủ trọng tâm.
- `irrelevant`: không giúp trả lời câu hỏi.

Cách tính đơn giản:

```text
Context Precision@K = relevant_chunks_in_top_k / K
```

Cách tính có trọng số:

```text
relevant = 1.0
partially_relevant = 0.5
irrelevant = 0.0
```

### 10.5 Context Recall Rubric

> Điều kiện tiên quyết: chỉ tính được khi retrieved context đã được expose (xem mục 2.4).

So retrieved context với `required_evidence`.

```text
Context Recall = matched_required_evidence / total_required_evidence
```

Có thể tính riêng:

- `Context Recall Must Have`
- `Context Recall All Evidence`

## 11. Output báo cáo

Báo cáo tổng hợp nên có:

- Faithfulness trung bình.
- Response Relevancy trung bình.
- Context Precision@K.
- Context Recall.
- Breakdown theo question category (factual, recommendation, comparison, follow-up, filter refinement,
  image/hybrid, clarification, unanswerable).
- Guardrail fail rate: tỷ lệ câu vi phạm guardrail (bịa product_id/giá/tồn kho, lộ thuật ngữ kỹ thuật).
- Follow-up success rate: tỷ lệ turn tham chiếu sản phẩm / filter refinement trả lời đúng ngữ cảnh.
- Danh sách câu trả lời hallucination (đặc biệt về giá/tồn kho/khuyến mãi).
- Danh sách câu trả lời đúng nhưng context recall thấp.
- Danh sách context precision thấp do retriever lấy nhiễu.
- Danh sách câu hỏi unanswerable mà chatbot vẫn bịa câu trả lời.

Schema summary:

```csv
run_id,metric,question_category,k,value,question_count,notes
```

Schema per-question:

```csv
run_id,question_id,category,faithfulness,response_relevancy,context_precision_at_k,context_recall,pass_fail,notes
```

## 12. Tiêu chí pass/fail đề xuất

Ngưỡng bản đầu tiên có thể đặt mềm để quan sát baseline:

- Faithfulness trung bình >= 4.0/5.
- Response Relevancy trung bình >= 4.0/5.
- Guardrail fail rate <= 5% (khớp ngưỡng hallucination trong `docs/chatbot.md`).
- Unanswerable hallucination rate <= 10%.
- Context Precision@5 >= 0.7 (chỉ tính khi đã expose context — xem mục 2.3).
- Context Recall must-have >= 0.8 (chỉ tính khi đã expose context — xem mục 2.4).

Với câu hỏi về giá/tồn kho:

- Không được khẳng định giá cuối / còn hàng / giảm giá khi context không có hoặc khi
  `warnings` báo `spring_boot_unavailable`.

Với câu hỏi unanswerable:

- Chatbot phải nói chưa hỗ trợ hoặc hướng người dùng kiểm tra chính sách, không được bịa.

## 13. Rủi ro và điểm cần chốt

- **Retrieved context chưa được API expose** — đây là blocker chính cho Context Precision/Recall.
  Nếu muốn đo hai metric này, ưu tiên số 1 là thêm field debug vào `AssistantChatResponse`
  (`schemas/assistant.py`) hoặc instrument workflow (`services/assistant/workflow.py`).
- Reference answer phải version theo snapshot dữ liệu, vì giá/tồn kho là source-of-truth động
  từ Spring Boot và có thể thay đổi giữa các lần chạy.
- LLM-as-a-judge có thể thiên lệch, nên cần human review để hiệu chỉnh rubric. Lưu ý judge cũng
  là Gemini nếu dùng chung provider — cân nhắc tách model judge để tránh self-preference bias.
- Recommendation khó có một đáp án duy nhất, nên cần reference answer dạng tiêu chí thay vì một câu cứng.
- Chatbot có gọi tool động (Spring Boot `check_product_availability`), cần lưu cả tool inputs/outputs
  để chấm faithfulness về tồn kho.
- Câu hỏi image/hybrid cần chuẩn bị ảnh mẫu và (tùy chọn) `crop_box`; kết quả phụ thuộc YOLO crop
  nên khó tái lập bằng text template — tách nhóm này khi phân tích.
- Nếu câu hỏi tiếng Việt có nhiều cách diễn đạt, nên bổ sung paraphrase set ở vòng sau.

## 14. Thứ tự triển khai đề xuất

1. Chốt snapshot metadata sản phẩm (Qdrant + DB Spring Boot) làm nguồn sự thật.
2. Chốt schema question/reference/evidence.
3. (Nếu muốn đo Context Precision/Recall) expose retrieved context qua field debug trong
   `AssistantChatResponse` hoặc instrument workflow. Nếu chưa làm, bỏ qua hai metric này và chỉ
   đo Faithfulness + Relevancy + Guardrail.
4. Tạo bộ 80 câu hỏi thử nghiệm đầu tiên (theo phân bổ mục 6.2), gồm cả nhóm follow-up nhiều lượt.
5. Viết reference answer và required evidence cho bộ này.
6. Viết eval runner mirror cấu trúc `evals/search_evaluation/text/scripts/`; dùng
   `service-ai/tests/integration/test_assistant_chat.py` làm mẫu cho hội thoại nhiều lượt cùng
   `session_id`.
7. Chạy chatbot với `GEMINI_TEMPERATURE=0`, log answer (+ context nếu đã expose).
8. Chấm thử bằng rubric thủ công cho một phần mẫu, rồi viết LLM-as-a-judge.
9. Tính metrics và xuất report (mirror `05_compute_metrics.py`).
10. So sánh baseline giữa các prompt/retriever/model.
