# Packet review A–C được lưu trữ (tùy chọn)

Ba biến thể A–C đã chạy đủ 80/80 câu. Các packet dưới đây được giữ nguyên để có thể tái sử dụng nếu sau này cần một đợt đánh giá thủ công; chúng không còn thuộc điều kiện nghiệm thu Conversational AI hiện hành.

## Reviewer A

- `llm_no_rag/review/reviewer_a_V3.csv`
- `rag_no_memory/review/reviewer_a_V1.csv`
- `rag_memory_rerank_off/review/reviewer_a_V4.csv`

## Reviewer B

- `llm_no_rag/review/reviewer_b_V3.csv`
- `rag_no_memory/review/reviewer_b_V1.csv`
- `rag_memory_rerank_off/review/reviewer_b_V4.csv`

Giữ nguyên `case_id`, câu hỏi, câu trả lời và evidence. Chỉ điền các cột chấm điểm/nhận xét theo rubric hiện hành. Với ca critical, phải điền cả các hard gate áp dụng; không dùng `pass/fail` trong cột điểm 1–5.

Nếu kích hoạt lại quy trình tùy chọn này, cần chạy lại bộ tổng hợp human validation và ghi rõ đó là bằng chứng bổ sung. Kết luận A–D hiện hành dựa trên ground truth đã duyệt, metric tự động và hard gate critical.
