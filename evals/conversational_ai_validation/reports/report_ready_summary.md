# Kết quả kiểm định Conversational AI

## Kết quả tự động hiện có

| Nhóm | Số câu | Mức tương đồng token-F1 với câu trả lời tham chiếu |
|---|---:|---:|
| Toàn bộ | 80 | 0,823 |
| Filter refinement | 10 | 0,666 |
| Follow-up ordinal | 10 | 0,652 |
| Nhóm khó | 12 | 0,638 |

Rule-based grounding: 1,000; Context Precision: 0,955; Context Recall: 1,000.

Điểm trung bình toàn bộ vượt ngưỡng kỹ thuật tạm thời 0,70, nhưng các nhóm Filter refinement, Follow-up ordinal và nhóm khó đều thấp hơn ngưỡng. Vì vậy Token-F1 chỉ được dùng như chỉ số chẩn đoán, không phải kết luận về tính hữu ích.

## Kiểm định bởi con người

Trạng thái: `user_confirmed_prescore`. Reviewer A hoàn tất 40/40 ca; Reviewer B hoàn tất 40/40 ca.

Mức đồng thuận quyết định đạt/không đạt: 1,000; Cohen's kappa: 1,000.

Ngưỡng Token-F1 được đề xuất sau hiệu chỉnh: 0,925.
Các con số đồng thuận và ngưỡng ở trên chỉ là AI pre-score minh họa, không đủ điều kiện đưa vào báo cáo cho đến khi hai reviewer con người xác nhận độc lập.

## Tiêu chí cứng

Trạng thái: `complete`; đã review 12/12 ca; kết quả hard gate: True.

## Đối chứng

- LLM không RAG: pending.
- RAG không memory: pending.
- RAG + search + memory: pending.
- Template từ dữ liệu sản phẩm (tùy chọn): pending.

Chỉ kết luận RAG làm giảm phát biểu không có căn cứ hoặc memory cải thiện khả năng giữ ràng buộc sau khi các baseline bắt buộc hoàn tất trên cùng tập câu hỏi và cấu hình.

## Kết quả tự động cho 12 ca critical

Automatic scorer đạt 12/12 ca. Human reviewer đã xác nhận 12/12 ca.

Người review đã xác nhận đủ 12/12 ca; hard gate đạt.
