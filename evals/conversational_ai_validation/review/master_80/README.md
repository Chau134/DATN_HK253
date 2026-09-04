# Review ground truth cho master-80-v2

Ground truth đã hoàn tất review và được khóa cho đủ 80 câu. Trạng thái chính thức nằm tại
`ground_truth_approval_summary.json` với `status=approved`; các file `ground_truth_review_pending.*`
được giữ làm dấu vết của vòng duyệt, không còn là danh sách công việc đang chờ.

Với mỗi dòng:

1. Kiểm tra question, reference answer, must-include/must-not-include và evidence JSON.
2. Với recommendation/follow-up, xác nhận các source product thực sự liên quan; sửa hoặc xóa evidence sai.
3. Đặt `question_status=approved`, `reference_status=approved` và
   `evidence_status=approved` sau khi nội dung đúng. Chỉ dùng `not_applicable` khi evidence JSON rỗng.
4. Điền `reviewer` và ghi ngắn gọn vào `review_notes` nếu có sửa nội dung.
5. Nếu chưa thể chấp nhận, dùng `needs_revision` hoặc `rejected`; không đặt `approved` theo mặc định.

`ground_truth_review_pending.md` là bản đọc thuận tiện. Quyết định phải được ghi vào CSV.

Sau khi review xong, chạy từ workspace root:

```powershell
python evals/conversational_ai_validation/scripts/11_apply_master_ground_truth_review.py
```

Script chỉ cập nhật ba file ground truth master sau khi cả 39 dòng hợp lệ và không còn trạng thái chờ.
Runner A--D hiện đã được phép chạy. Cấu hình D hậu sửa đã hoàn tất; A--C vẫn chưa thực hiện.
