# Hướng dẫn review kết quả D hậu sửa

## Trạng thái cuối

Review đã hoàn tất ngày 27/08/2026:

- Reviewer A: 80/80 ca hoàn tất.
- Reviewer B: 80/80 ca hoàn tất.
- Đồng thuận quyết định đạt/không đạt: 80/80, Cohen's kappa = 1,000.
- Kết quả: 73 ca đạt, 7 ca không đạt; không còn ca cần phân xử.
- Scorer: `status=complete`, `provenance=independent_human_review`,
  `report_eligible=true`.

Phần dưới đây được giữ lại để truy vết quy trình chấm.

Hai reviewer chấm **độc lập** trên hai file:

- `reviewer_a_final.csv`
- `reviewer_b_final.csv`

Chỉ cần chấm lại các dòng có `review_notes` bắt đầu bằng `CẦN CHẤM LẠI HẬU SỬA`.
Các dòng còn lại đã được kế thừa từ vòng review V2 vì câu trả lời, lịch sử hội thoại
và context truy hồi không thay đổi.

## Phạm vi cần chấm lại

Tổng cộng **45/80 ca cho mỗi reviewer**:

| Nhóm | Số ca |
|---|---:|
| `critical_product` | 2 |
| `filter_refinement` | 10 |
| `followup_ordinal` | 10 |
| `product_comparison` | 8 |
| `product_factual` | 1 |
| `product_recommendation` | 14 |

Danh sách rút gọn nằm trong `review_required_final.csv`.

## Cách điền

- Các tiêu chí chất lượng áp dụng: nhập điểm nguyên từ **1 đến 5** theo
  `evals/conversational_ai_validation/review/RUBRIC.md`.
- `task_success`, `context_retention` và `refusal_correctness`: ghi `NA` nếu tiêu chí
  không áp dụng cho ca đang chấm.
- Các cột hard gate `critical_*`: nhập `pass` hoặc `fail` khi áp dụng; ghi `NA` nếu
  không áp dụng.
- Reviewer A và B không xem hoặc sao chép điểm của nhau trước khi hoàn tất.
- Token-F1 chỉ là chỉ số tương đồng từ vựng chẩn đoán, không dùng để quyết định điểm
  chất lượng của reviewer.

Kết quả cuối đã được tạo bởi `scripts/02_score_review.py` với
`review_config_final.json` và được ghi vào các tệp `human_validation_*` trong thư mục
`reports` của cấu hình hậu sửa.
