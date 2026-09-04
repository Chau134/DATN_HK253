# Conversational AI Evaluation

## Eval trace và audit evaluator (v4)

Để chạy acceptance với context thật, bật `ASSISTANT_EVAL_TRACE_ENABLED=true` chỉ trên
instance evaluation; production giữ mặc định `false`. Trace allow-list product evidence, băm
`session_id`/`request_id`, và không chứa transcript, `user_id` hay preference note.

```powershell
python scripts/07_run_rag_eval.py --endpoint http://localhost:8000/assistant/chat --retries 0 --require-evaluation-trace
python scripts/08_compute_rag_metrics.py
python scripts/11_audit_evaluator.py --prepare
# Điền hai cột human_* trong reports/evaluator_manual_audit.csv, rồi chạy:
python scripts/11_audit_evaluator.py
```

Report v4 dùng `rule_based_grounding_score` và `token_f1_relevancy`. Context Precision/Recall
chỉ là release gate khi 100% case có `context_mode=full_context`; các metric
`*_product_id_proxy` chỉ dùng chẩn đoán. Runner ghi `rag_eval_run_metadata.json` với commit,
catalog, collection, model config, endpoint, seed, timestamp và evaluator version.

Thư mục này chứa workflow thực thi cho Conversational AI (chatbot/RAG) theo plan ở
[conversational_ai_evaluation.md](conversational_ai_evaluation.md).

Phạm vi đã triển khai gồm sinh testcase/reference/evidence, RAG runner với metrics heuristic,
behavioral eval, long-session eval và evaluation trace chứa full context chạy trực tiếp qua API.
LLM-as-a-judge và safety/fault-injection suite chuyên biệt vẫn là future work.

> **Trạng thái review ngày 2026-08-25:** packet 80 câu đã qua structural validation. 70 question/
> reference/evidence cũ vẫn `approved`; 8 case `shop_knowledge` và 2 case `unanswerable` mới đang
> `pending` và phải được review thủ công trước khi dùng kết quả làm release acceptance. Báo cáo
> evaluator audit cũ chưa bao phủ category mới nên cần audit lại sau khi ground truth được duyệt.

## Luồng tạo testcase

### Rebuild và chấm 4 RAG metrics trên 1.000 sản phẩm MySQL

```powershell
$env:MYSQL_PWD = "<mysql-password>"
python scripts/06_export_mysql_snapshot.py
python scripts/02_generate_questions.py
python scripts/03_create_reference_answers.py
python scripts/07_run_rag_eval.py --endpoint http://localhost:8000/assistant/chat
python scripts/08_compute_rag_metrics.py
```

`08_compute_rag_metrics.py` hiện xuất các trường Faithfulness, Response Relevancy, Context
Precision và Context Recall theo từng câu, category, difficulty và toàn bộ suite. Faithfulness và
Response Relevancy hiện là heuristic dựa trên required-term coverage, forbidden claim, product-ID
grounding và token-F1; chưa phải semantic LLM-as-a-judge. Trong report/thiết kế mới, điểm
Faithfulness heuristic nên được trình bày là `rule_based_grounding_score` để tránh diễn giải quá mức.
Khi API trả `retrieved_context` hoặc `product_context`, context metrics được chấm
ở chế độ `full_context`. Với contract hiện tại chỉ trả `product_ids`, runner tái
dựng metadata từ snapshot và báo rõ `context_mode=product_id_proxy`; Precision /
Recall lúc này là proxy ở mức sản phẩm, không bị trình bày nhầm thành chunk-level.

Ngưỡng mặc định: Faithfulness >= 0.85, Response Relevancy >= 0.70,
Context Precision >= 0.60 và Context Recall >= 0.80.

Nguồn dữ liệu gồm snapshot sản phẩm đã index và knowledge xác định từ footer/chính sách của
Mystery Closet. Catalog overview lấy category/count từ snapshot khi sinh ground truth và từ facet
Qdrant `active=true, available=true` ở runtime. Snapshot sản phẩm ban đầu tái dùng
`../search_evaluation/image/data/product_snapshot.csv` (3638 sản phẩm, có
`product_id, product_name, product_display_name_vi, category, brand, color, material, gender,
is_active, description`).

1. Chạy `scripts/01_build_product_snapshot.py` để chuẩn hóa snapshot về schema
   `ConvProductRecord` và đóng dấu `version` (mặc định timestamp) cho tái lập:

   ```bash
   python scripts/01_build_product_snapshot.py
   ```

   Output `data/product_snapshot.csv` + `reports/snapshot_summary.json`.

2. Chạy `scripts/02_generate_questions.py` để sinh question set theo các nhóm text-feasible:

   ```bash
   python scripts/02_generate_questions.py
   ```

   Output `data/question_set.csv` theo schema
   `question_id,session_id,turn_index,category,question,expected_answer_type,entity_ids,depends_on_history,difficulty,manual_status,notes,reviewer,reviewed_at,review_notes`.
   Các câu follow-up nhiều lượt (ordinal, filter refinement) dùng chung `session_id` và tăng
   `turn_index`; `depends_on_history=true` cho lượt phụ thuộc ngữ cảnh.

3. Chạy `scripts/03_create_reference_answers.py` để sinh reference answer + required evidence:

   ```bash
   python scripts/03_create_reference_answers.py
   ```

   Output `data/reference_answers.csv`
   (`question_id,reference_answer,answer_must_include,answer_must_not_include,reference_source_ids,review_status,notes,reviewer,reviewed_at,review_notes`)
   và `data/required_evidence.csv`
   (`question_id,evidence_id,source_id,evidence_text,evidence_role,required_level,notes,review_status,reviewer,reviewed_at,review_notes`).

4. **Review thủ công**: tạo review packet (không tự động approve):

   ```bash
   python scripts/09_ground_truth_review.py prepare
   ```

   Chỉnh `review/ground_truth_review.csv`; dùng
   `review/ground_truth_review.md` để đọc question, reference, evidence và source product thuận tiện.
   Với mỗi dòng, đặt `question_status`, `reference_status`, `evidence_status` thành `approved`,
   `needs_revision` hoặc `rejected`, đồng thời điền `reviewer` và `review_notes`. Evidence rỗng dùng
   `not_applicable`.

   Kiểm tra packet sau khi sửa:

   ```bash
   python scripts/09_ground_truth_review.py validate --require-complete
   ```

   Chỉ sau khi validator pass mới import quyết định vào ba file ground truth:

   ```bash
   python scripts/09_ground_truth_review.py apply
   ```

   Lệnh `prepare` từ chối ghi đè packet đã tồn tại; chỉ dùng `--force` khi chắc chắn muốn bỏ toàn bộ
   nội dung review đang làm. Testcase chỉ được dùng làm release acceptance khi question, reference
   và evidence đều `approved` (`evidence_status=not_applicable` được chấp nhận nếu evidence rỗng).

5. Chạy behavioral eval cho small-talk, độ lặp và preference recall qua session mới:

   ```bash
   python scripts/04_run_behavioral_eval.py \
     --endpoint http://localhost:8080/api/assistant/chat
   ```

   Case nằm trong `configs/behavioral_cases.json`. Output gồm
   `reports/behavioral_results.csv` và `reports/behavioral_summary.json`, với các metric
   `turn_pass_rate`, `small_talk_no_retrieval_rate`, `preference_recall_rate` và
   `exact_small_talk_response_repeat_rate`. Threshold trong file case khiến script trả exit code
   khác `0` khi chất lượng tụt dưới mức đã đặt. Có thể truyền access token qua
   `EVAL_BEARER_TOKEN`.

6. Chạy acceptance eval cho memory phiên dài:

   ```bash
   python scripts/long_session_eval.py \
     --endpoint http://localhost:8000/assistant/chat
   ```

   Cấu hình `configs/long_session_cases.json` có 10 session chính, mỗi session 20
   lượt chạy tuần tự. Mỗi session đặt sentinel ở đầu/giữa/cuối, sửa một constraint,
   tham chiếu danh sách gần nhất và danh sách có tên, sau đó chạy thêm probe
   cross-session/cross-user. Runner chấm riêng `early_recall`, `middle_recall`,
   `recent_recall`, `correction_supersedes_old_value`, `reference_resolution`,
   `cross_session_preference_recall`, `session_isolation`, `false_memory_rate`,
   availability grounding và latency.

   Run ID là hash ổn định của cấu hình. Output nằm tại
   `reports/long_session/<run_id>/`, gồm `summary.json`,
   `transcript.redacted.jsonl`, `probe_results.jsonl` và
   `checkpoint_statistics.json`. Nên gọi endpoint FastAPI trực tiếp để các trường
   `request_id`/`turn_sequence` được kiểm tra đầy đủ; gateway Spring Boot cần forward
   hai trường này trước khi dùng cho acceptance chính thức.

## Nhóm câu hỏi (bản đầu tiên)

Chỉ gồm nhóm text-feasible với dữ liệu hiện có (không có giá/tồn kho/ảnh):

- `product_factual` — hỏi thuộc tính (màu, chất liệu, giới tính, danh mục).
- `product_comparison` — so sánh 2 sản phẩm.
- `product_recommendation` — tư vấn theo nhu cầu (reference dạng tiêu chí).
- `followup_ordinal` — hội thoại 2 lượt: search rồi tham chiếu ordinal ("cái thứ 2 thì sao").
- `filter_refinement` — hội thoại 2 lượt: search rồi tinh chỉnh filter ("màu đen thì sao").
- `shop_knowledge` — tên/địa chỉ shop, catalog overview và chính sách vận chuyển, đổi trả,
  thanh toán, bảo hành; kỳ vọng trả lời xác định từ nguồn shop, không chuyển sang tìm sản phẩm.
- `unanswerable` — tuyên bố không có căn cứ (cam kết công dụng, người nổi tiếng sử dụng), kỳ vọng
  chatbot từ chối xác nhận thay vì bịa.

Bị loại khỏi bản đầu (future work): availability follow-up và image/hybrid chat, vì cần
tồn kho realtime từ Spring Boot và ảnh mẫu.

## Guardrail

Mỗi reference answer đều seed `answer_must_not_include` bằng các vi phạm guardrail lấy từ
`_assistant_reply_prompt` (`service-ai/services/llm/service.py`): không bịa product_id,
không khẳng định tồn kho/giá/giảm giá khi context không có, không lộ thuật ngữ kỹ thuật.
Evaluator v4 kiểm tra cả guardrail chung lẫn từng cụm `answer_must_not_include` của reference;
case catalog overview cấm rõ các danh mục không có như ví da, túi xách, balo và giày dép.

## Cấu trúc

```text
conversational_ai_evaluation/
  README.md
  conversational_ai_evaluation.md
  test_rag_metrics.py
  test_long_session_eval.py
  configs/
    conversational_ai.yaml
    behavioral_cases.json
    long_session_cases.json
  data/
  review/
    ground_truth_review.csv
    ground_truth_review.md
    ground_truth_review_summary.json
  reports/
  scripts/
    common.py
    01_build_product_snapshot.py
    02_generate_questions.py
    03_create_reference_answers.py
    04_run_behavioral_eval.py
    05_run_long_session_eval.py
    06_export_mysql_snapshot.py
    07_run_rag_eval.py
    08_compute_rag_metrics.py
    09_ground_truth_review.py
    long_session_eval.py
```

## Ghi chú

File cấu hình `conversational_ai.yaml` dùng syntax JSON hợp lệ để các script đọc bằng thư viện
chuẩn của Python mà không cần thêm dependency (giống `search_evaluation`).
