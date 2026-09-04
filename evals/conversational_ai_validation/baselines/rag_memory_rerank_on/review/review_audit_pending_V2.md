# Audit pending — Reviewer A/B V2

Trạng thái: **đã sửa điểm/gate và áp dụng lại rubric; còn chờ xử lý tính độc lập
của 21 nhãn Reviewer B và chạy lại output sau bản sửa chatbot**.

Các sửa dưới đây đã được áp dụng vào cả hai packet; validation framework đạt 13/13 test.

## 1. Lỗi cấu trúc đã sửa

Các cột điểm chỉ nhận 1–5 hoặc NA; hard gate chỉ nhận pass, fail hoặc NA.

| Question ID | Sửa/kiểm tra lại |
|---|---|
| critical-policy-001 | refusal_correctness=5 cho A và B; hiện đang để trống. |
| critical-policy-002 | A: đổi refusal_correctness từ pass thành 5. B: answer trùng reference và đúng evidence chính sách chính thức, vì vậy cần chấm lại factual/groundedness/relevancy/completeness/refusal/helpfulness = 5, critical_policy=pass, critical_clarification_or_refusal=pass. |
| critical-product-001 | refusal_correctness=5 cho A/B; critical_product_exists=pass. Reviewer A đang đặt nhầm fail. |
| critical-product-002 | refusal_correctness=5 cho A/B; critical_product_exists=pass. Reviewer A đang đặt nhầm fail. |
| conv-una-v2-0001-t0 | refusal_correctness=4, không phải pass. Câu từ chối đúng nhưng thiếu bước tiếp theo; theo rubric, completeness=4, helpfulness=4. |
| conv-una-v2-0002-t0 | refusal_correctness=4, không phải pass. Câu từ chối đúng nhưng thiếu bước tiếp theo; theo rubric, completeness=4, helpfulness=4. |
| conv-shop-0004-t0 | critical_stock=NA; cụm “nếu còn hàng” là điều kiện chính sách, không phải khẳng định tồn kho của một sản phẩm. |
| conv-flt-0005-t1 | critical_price=fail; hiện đang để trống. Câu trả lời không chứng minh sản phẩm rẻ hơn và còn mất danh mục/màu của lượt trước. |

## 2. Áp dụng thống nhất rubric

### So sánh sản phẩm

Các ca conv-cmp-0001-t0 đến conv-cmp-0008-t0 chỉ liệt kê thuộc tính, không nêu kết luận
giống/khác. Rubric quy định completeness=3 và task_success=4.

Không nên luân phiên B-strict/B-lenient giữa các câu có cùng cấu trúc.

### Follow-up ordinal

Các ca sau tham chiếu đúng sản phẩm và đã nêu đủ danh mục, màu, chất liệu, giới tính:

- conv-ord-0001-t1
- conv-ord-0002-t1
- conv-ord-0003-t1
- conv-ord-0004-t1
- conv-ord-0005-t1

Reference không bắt buộc giá/tồn kho, vì vậy completeness=5. Không hạ điểm chỉ vì thiếu chi tiết
tùy chọn.

### Ràng buộc màu/danh mục cần review lại

Theo rubric, sản phẩm sai màu chính có thể vẫn đúng dữ kiện về chính nó
(factual_correctness, groundedness), nhưng answer_relevancy, task_success và helpfulness thường
không quá 2–3.

| Nhóm | Question ID | Vấn đề |
|---|---|---|
| Màu kết hợp | conv-flt-0002-t0 | Yêu cầu Đỏ/Trắng nhưng 3/3 kết quả chỉ Trắng. |
| Màu kết hợp | conv-ord-0001-t0 | Yêu cầu Nâu/Trắng ngà nhưng 3/3 kết quả chỉ Trắng ngà. |
| Màu kết hợp | conv-rec-0016-t0 | Yêu cầu Hồng/Trắng nhưng 3/3 kết quả chỉ Trắng. |
| Chỉ 1 kết quả đúng màu | conv-flt-0005-t0 | Vani: chỉ 1/3 đúng, hai sản phẩm còn lại là Trắng ngà/Trắng. |
| Chỉ 1 kết quả đúng màu | conv-ord-0004-t0 | Cát/Đen: chỉ 1/3 đúng màu kết hợp. |
| Chỉ 1 kết quả đúng màu | conv-rec-0002-t0 | Chàm: chỉ 1/3 đúng; hai kết quả còn lại Xám đá/Khaki. |
| Chỉ 1 kết quả đúng màu | conv-rec-0003-t0 | Nâu sọc: chỉ 1/3 đúng chính xác. |
| Chỉ 1 kết quả đúng màu | conv-rec-0005-t0 | Đỏ rượu vang: chỉ 1/3 đúng chính xác. |
| Chỉ 1 kết quả đúng màu | conv-rec-0008-t0 | Hồng pastel: chỉ 1/3 đúng chính xác. |
| Chỉ 1 kết quả đúng màu | conv-rec-0010-t0 | Vàng ánh kim: chỉ 1/3 đúng chính xác. |
| Chỉ 1 kết quả đúng màu | conv-rec-0018-t0 | Nâu thuốc lá: chỉ 1/3 đúng chính xác. |
| Không có màu đúng chính xác | conv-rec-0019-t0 | Yêu cầu Nâu đậm; kết quả là Nâu, Nâu/Nâu xám, Nâu chocolate. |
| Một kết quả lệch shade | conv-flt-0004-t0 | Xanh dương nhạt: kết quả thứ ba là Trắng ngà/Xanh dương. |
| Hai kết quả lệch shade | conv-ord-0002-t0 | Xám than: hai kết quả sau là Xám nhạt/Xám trung bình. |

## 3. Các ca lỗi filter đã được hai reviewer nhận diện đúng

Các ca conv-flt-0001-t1 đến conv-flt-0005-t1 thuộc output trước khi chatbot được sửa.
Chúng phải giữ trạng thái không đạt. Khác biệt 1 điểm giữa A/B về mức độ nghiêm trọng có thể giữ
nguyên nếu là đánh giá độc lập; riêng hard gate bị trống phải sửa theo mục 1.

## 4. Tính độc lập của reviewer

Reviewer B còn 21 ghi chú dạng [B] B-strict/B-lenient; 20 ghi chú B bắt đầu bằng nguyên văn ghi
chú A. Cần:

1. Reviewer B đọc lại packet mà không xem điểm/ghi chú A.
2. Xóa nhãn strict/lenient và ghi lý do dựa trực tiếp trên rubric/evidence.
3. Sau khi khóa hai packet, mới chạy scorer để tính exact agreement, within-one và Cohen's kappa.

## 5. Điều kiện trước khi cập nhật chương 09

- Mọi trường điểm/gate hợp lệ và không còn ô bắt buộc trống.
- Hai reviewer xác nhận độc lập.
- Các bất đồng làm thay đổi đạt/không đạt được adjudicate.
- Không dùng packet V2 này để đại diện cho chatbot sau bản sửa: đây là output trước sửa. Muốn báo
  cáo chất lượng phiên bản cuối, cần chạy lại cấu hình D và tạo packet mới từ response sau sửa.
