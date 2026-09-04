# Chatbot evaluation nâng cao trên 100 sản phẩm

Bộ eval này dùng đúng 100 sản phẩm trong `database/100.sql`, gồm **305 lượt
test / 295 session**. Đây là bộ mặc định duy nhất trong thư mục
`evals/chatbot_100_products`; kết quả chạy mới ghi đè kết quả cũ của chính thư
mục này và không liên quan đến `evals/conversational_ai_evaluation`.

## Phạm vi bộ nâng cao

| Nhóm | Số lượt | Kỳ vọng chính |
|---|---:|---|
| Exact title | 100 | Tìm một ID có tên tương đương |
| Tên không dấu | 30 | Chịu được câu lệnh và tên không dấu |
| Tên có typo | 20 | Chịu được lỗi thiếu một ký tự |
| Keyword search | 30 | Trả một sản phẩm đúng `category + keyword` |
| Attribute search | 30 | Trả một sản phẩm đúng `category + attribute` |
| Use-case recommendation | 20 | Gợi ý đúng `category + use case` |
| Factual grounding | 20 | Retrieve đúng ID và nêu dữ kiện đã index |
| Comparison | 10 | Cả hai ID phải có trong Top K |
| Multi-turn | 20 lượt / 10 session | Dùng tham chiếu lượt trước hoặc giữ category khi refine |
| Small-talk/capability | 8 | Trả lời phù hợp, không tự trả product card |
| Policy uncertainty | 8 | Không bịa chính sách, cam kết hoặc giao dịch |
| Prompt injection | 4 | Không tiết lộ prompt, credential, cấu hình nội bộ |
| Ngoài catalog | 5 | Không trả sản phẩm thời trang không liên quan |

Ground truth không ép một ID duy nhất cho truy vấn có nhiều đáp án hợp lệ.
Các case keyword, attribute và use case dùng tập ID cùng category có cùng intent.
Các sản phẩm trùng tên cũng được chấm theo tập ID tương đương.

## Sinh và kiểm tra test case

Từ thư mục gốc repository:

```powershell
python evals/chatbot_100_products/run_eval.py --prepare-only
python -m pytest evals/chatbot_100_products/test_run_eval.py -q
```

File sinh ra:

- `data/products.csv`: snapshot metadata của 100 sản phẩm.
- `data/test_cases.csv`: 305 lượt test và ground truth.

Generation dùng seed mặc định `42`, nên danh sách case có tính lặp lại. Có thể
đổi bằng `--seed`, nhưng khi so sánh hai lần chạy nên giữ nguyên seed.

## Chạy bộ nâng cao

```powershell
python evals/chatbot_100_products/run_eval.py `
  --base-url http://localhost:8080 `
  --concurrency 2 `
  --timeout 120
```

Runner chạy các session song song nhưng luôn chạy tuần tự các lượt trong cùng
session. Các tùy chọn:

- `--resume`: chỉ bỏ qua session đã hoàn tất toàn bộ lượt; session dở dang được
  chạy lại từ lượt đầu để khôi phục đúng hội thoại.
- `--report-only`: dựng lại báo cáo từ `data/results.jsonl`.
- `--bearer-token` hoặc biến `EVAL_BEARER_TOKEN`: xác thực endpoint nếu cần.
- `--top-k`, `--retries`, `--seed`: điều chỉnh cách chạy/chấm.

Runner kiểm tra readiness tổng và hai capability chatbot cần dùng:
`text_search` và `assistant_llm`. HTTP 503 được giữ nguyên là `status_code: 503`
trong run context.

## Kết quả bộ nâng cao

- `data/results.jsonl`: response và kết quả chấm từng lượt.
- `data/ranked_results.csv`: sản phẩm trả về theo rank.
- `data/manual_review.csv`: rubric 1–5 cho faithfulness, relevance,
  completeness và chất lượng comparison; không thay thế retrieval gates.
- `reports/run_context.json`: cấu hình và readiness lúc chạy.
- `reports/summary.json`: metric tổng, metric từng scenario và gates.
- `reports/assessment.md`: báo cáo Markdown và case thất bại.

Acceptance mặc định yêu cầu đủ 305 lượt, HTTP và câu trả lời không rỗng 100%,
retrieval đạt ít nhất 85%, tổng case pass ít nhất 80%, safety/out-of-catalog ít
nhất 90%, follow-up multi-turn ít nhất 80%, factual grounding 20/20, comparison
lấy đủ hai sản phẩm 10/10, không degraded, không trùng ID và p95 không quá 30
giây.

Evaluator giữ retrieval deterministic, kiểm tra riêng grounded claim
material/color trên factual track và phân loại lỗi chatbot, dependency/provider,
hoặc case cần audit lại ground truth. Các khía cạnh văn phong, mức hữu ích và
faithfulness ngữ nghĩa sâu vẫn cần calibrated LLM-as-judge hoặc manual review.
