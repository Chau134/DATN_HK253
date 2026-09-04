# Text-search robustness evaluation for the 100-product pilot

Suite dùng đúng 100 sản phẩm trong `database/100.sql`, nhưng query không còn là
display name nguyên văn. Mỗi sản phẩm được gán xác định vào một trong bốn phép
biến đổi:

- `accentless_title`: bỏ dấu và chuyển chữ thường;
- `conversational_title`: đặt tiêu đề trong câu nói của người mua;
- `reordered_keywords`: đảo thứ tự các từ khóa;
- `minor_typo`: bỏ một ký tự trong từ dài và bỏ gender token cuối.

Có 25 query cho mỗi nhóm. Duplicate title được chấm theo
`acceptable_product_ids`; rank của đúng source product vẫn được lưu riêng.
`query_id` chứa product ID thay vì số thứ tự trong snapshot, nhờ đó judgment
của một snapshot cũ không bị gán nhầm khi `database/100.sql` được lấy mẫu lại.

## Chuẩn bị dữ liệu

```powershell
python evals/text_search_100_products/run_eval.py --prepare-only
```

Lệnh chỉ sinh lại `data/products.csv` và `data/test_cases.csv`, không ghi đè kết
quả benchmark gần nhất.

## Chạy benchmark

```powershell
python evals/text_search_100_products/run_eval.py `
  --run-id text-search-advanced-<timestamp>
```

Runner kiểm tra `/health/ready/text_search`, smoke test trực tiếp service-ai và
qua public Spring API, kiểm tra instance ID định kỳ và fail-fast khi có fallback
hoặc restart. Preflight/degraded run trả exit code 2; quality gate fail trả exit
code 1.

Các ngưỡng chính:

- Hit@1 >= 70%;
- Hit@5 >= 90%;
- Hit@5 từng nhóm >= 80%;
- NDCG@5 >= 0,90;
- semantic judgment coverage@5 = 100%;
- p95 <= 3 giây;
- không HTTP error, fallback, duplicate hay empty positive result.

Tạo lại báo cáo từ raw result:

```powershell
python evals/text_search_100_products/run_eval.py --report-only
```

## Ground truth semantic

Grade:

- `3`: rất liên quan;
- `2`: liên quan;
- `1`: liên quan một phần;
- `0`: không liên quan.

Quy trình khi ranking sinh candidate mới:

```powershell
python evals/text_search_100_products/suggest_semantic_grades.py
```

Review `data/semantic_review_candidates.csv`, sửa `relevance_grade` và notes nếu
cần, rồi promote:

```powershell
python evals/text_search_100_products/suggest_semantic_grades.py --approve-all-drafts
python evals/text_search_100_products/run_eval.py --report-only
```

Script promotion merge với judgment lịch sử thay vì xóa những candidate không
còn trong Top-5.

## Output

- `data/products.csv`: snapshot 100 sản phẩm;
- `data/test_cases.csv`: 100 advanced query;
- `data/results.jsonl`: raw normalized response;
- `data/ranked_results.csv`: một dòng cho mỗi result;
- `data/semantic_review_candidates.csv`: review sheet Top-5 hiện tại;
- `config/semantic_judgments.json`: ground truth semantic chính thức;
- `reports/summary.json`: metrics tổng và theo query type;
- `reports/assessment.md`: kết quả acceptance gate;
- `reports/run_context.json`: health, instance và cấu hình run.

Run improvement ngày 27/07/2026 là
`text-search-100-products-20260727-typo-recovery-v1`: Hit@1 99%, Hit@5 100%,
`minor_typo` Hit@1/Hit@5 96%/100%, NDCG@5 0,9823, coverage 100%, p95
1,195 giây và acceptance gate PASS. Run hoàn thành 100 query trên cùng một instance,
không HTTP error, fallback, warning, empty result hoặc duplicate ID.
