# Hướng dẫn chấm điểm 1–5

Reviewer chỉ đánh giá câu trả lời từ nội dung trong packet: câu hỏi, lịch sử hội thoại, reference,
evidence và retrieved context. Không dùng kiến thức bên ngoài để “sửa hộ” hệ thống.

## Ý nghĩa chung

| Điểm | Quyết định thực tế |
|---:|---|
| 5 | Hoàn toàn đúng, đầy đủ và dùng được ngay; không có lỗi đáng kể. |
| 4 | Chấp nhận được; có lỗi/thiếu sót nhỏ nhưng không làm sai nhiệm vụ. |
| 3 | Đúng một phần; cần sửa trước khi coi là câu trả lời tốt. |
| 2 | Có lỗi lớn hoặc bỏ lỡ ràng buộc chính; phần lớn nhiệm vụ chưa hoàn thành. |
| 1 | Sai nghiêm trọng, lạc đề, mâu thuẫn nguồn hoặc bịa thông tin. |
| NA | Tiêu chí không áp dụng cho ca này. Giữ nguyên `NA`, không đổi thành điểm. |

Ngưỡng chấp nhận là **4**. Một ca chỉ đạt khi mọi tiêu chí áp dụng đều từ 4 trở lên và không có
hard gate nào `fail`. Không lấy điểm trung bình để bù một tiêu chí yếu.

## Mốc điểm theo từng tiêu chí

### `factual_correctness`

- 5: mọi tên, thuộc tính, giá, tồn kho, con số và chính sách đều đúng nguồn.
- 4: có diễn đạt hơi thiếu chính xác nhưng không thay đổi ý nghĩa hoặc quyết định của người dùng.
- 3: phần cốt lõi đúng nhưng có một dữ kiện phụ sai/không chắc chắn.
- 2: sai ít nhất một dữ kiện/ràng buộc chính.
- 1: bịa sản phẩm, giá, tồn kho, chính sách hoặc trả lời trái trực tiếp với nguồn.

### `groundedness`

- 5: mọi khẳng định kiểm chứng được đều có trong retrieved context/evidence.
- 4: có một chi tiết phụ không được nguồn nói rõ nhưng không ảnh hưởng kết luận.
- 3: có một khẳng định đáng kể thiếu bằng chứng; phần còn lại có căn cứ.
- 2: nhiều khẳng định thiếu bằng chứng hoặc suy diễn quá mức.
- 1: câu trả lời chủ yếu không có căn cứ hoặc mâu thuẫn nguồn.

### `answer_relevancy`

- 5: trả lời trực tiếp đúng câu hỏi và mọi ràng buộc, không lan man.
- 4: đúng trọng tâm, chỉ có một ít nội dung thừa.
- 3: trả lời được một phần nhưng bỏ sót một ý đáng kể.
- 2: bỏ lỡ ràng buộc trung tâm, dù nội dung cùng chủ đề.
- 1: lạc đề hoặc không trả lời câu hỏi.

### `completeness`

- 5: có toàn bộ `answer_must_include` và các ý bắt buộc trong reference/evidence.
- 4: đủ các ý bắt buộc; chỉ thiếu chi tiết tùy chọn.
- 3: thiếu một ý bắt buộc hoặc thiếu kết luận tổng hợp quan trọng.
- 2: thiếu nhiều ý bắt buộc hoặc chỉ trả lời một phần nhỏ.
- 1: gần như không chứa nội dung cần thiết.

### `task_success`

- 5: người dùng có thể tìm/chọn/so sánh/tinh chỉnh sản phẩm ngay từ câu trả lời.
- 4: nhiệm vụ hoàn thành, chỉ cần người dùng tự suy luận hoặc thao tác nhỏ.
- 3: nhiệm vụ hoàn thành một phần; cần hỏi/sửa thêm một lượt.
- 2: vi phạm ràng buộc chính nên kết quả khó dùng.
- 1: không tạo được tiến triển cho nhiệm vụ.

### `context_retention`

- 5: giữ đúng mọi ràng buộc, thứ tự và sửa đổi từ các lượt trước.
- 4: giữ đúng ngữ cảnh chính, chỉ thiếu một chi tiết phụ.
- 3: nhớ được một phần nhưng làm mất một ràng buộc đáng kể.
- 2: mất ràng buộc chính hoặc cập nhật sai filter/tham chiếu.
- 1: chọn sai đối tượng, dùng giá trị cũ đã bị sửa hoặc không dùng lịch sử.

Chỉ chấm tiêu chí này khi `conversation_history` có nội dung và ô không phải `NA`.

### `refusal_correctness`

- 5: từ chối đúng, giải thích giới hạn và đưa bước tiếp theo hợp lý.
- 4: từ chối đúng nhưng hơi ngắn hoặc thiếu một gợi ý hỗ trợ.
- 3: thể hiện không chắc chắn nhưng ranh giới từ chối chưa rõ.
- 2: vừa dè dặt vừa đưa ra một phần khẳng định không có nguồn.
- 1: tự tin xác nhận/bịa thông tin không thể trả lời.

### `helpfulness`

- 5: rõ ràng, súc tích, dễ hành động và phù hợp nhu cầu.
- 4: hữu ích và dễ hiểu, còn một cải thiện nhỏ về giải thích/cấu trúc.
- 3: dùng được một phần nhưng mơ hồ, thiếu lý do hoặc thiếu bước tiếp theo.
- 2: ít giá trị thực tế do thiếu/sai ràng buộc quan trọng.
- 1: gây hiểu nhầm, khó hiểu hoặc có thể dẫn người dùng đến quyết định sai.

## Hard gate

Các cột `critical_*` dùng `pass`, `fail` hoặc `NA`, không dùng điểm 1–5:

- `critical_price`: giá/giảm giá và ràng buộc rẻ–đắt phải đúng context.
- `critical_stock`: trạng thái còn/hết hàng và size phải đúng context.
- `critical_product_exists`: sản phẩm được giới thiệu phải tồn tại trong nguồn phù hợp.
- `critical_policy`: không thêm hoặc khẳng định chính sách ngoài evidence.
- `critical_clarification_or_refusal`: câu không thể trả lời phải từ chối/yêu cầu làm rõ.

Một hard gate `fail` khiến ca không đạt ngay cả khi các điểm khác đều là 5.

## Quy tắc xử lý tình huống thường gặp

- Dữ kiện đều đúng nhưng không nêu rõ kết luận giống/khác khi được yêu cầu so sánh: thường
  `completeness=3`, `task_success=4`.
- Sản phẩm tồn tại nhưng sai màu/size/ngân sách chính: factual có thể vẫn đúng với chính sản phẩm,
  nhưng `answer_relevancy`, `task_success` và `helpfulness` thường không quá 2–3.
- Có một câu chính sách không có trong evidence: hạ `groundedness`, đồng thời
  `critical_policy=fail`.
- Câu từ chối đúng nhưng không đề xuất cách tiếp tục: `refusal_correctness=4`, `helpfulness=4`.
