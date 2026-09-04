# Nội dung thuyết trình — Phần Sản phẩm và demo

Tổng thời lượng gợi ý cho slide 17–21: **6–7 phút**, trong đó video demo nên dài **3–4 phút**.

## Slide 17 — Tổng quan sản phẩm hoàn thiện

**Thông điệp:** Kết quả là một hệ thống hoàn chỉnh gồm cửa hàng, trợ lý AI và backoffice.

**Lời dẫn gợi ý (40–50 giây):**

> Từ kiến trúc đã trình bày, nhóm hiện thực ba không gian trải nghiệm. Cửa hàng trực tuyến phục vụ toàn bộ hành trình mua sắm. Trợ lý AI cung cấp tìm kiếm và tư vấn đa phương thức. Backoffice giúp quản trị dữ liệu, đơn hàng và đồng bộ chỉ mục. Ba khu vực dùng chung dữ liệu và quy tắc nghiệp vụ.

## Slide 18 — Chức năng nổi bật thứ nhất

**Thông điệp:** Một giao diện hỗ trợ Text Search, Image Search và Hybrid Search.

**Lời dẫn gợi ý (55–65 giây):**

> Người dùng có thể diễn đạt nhu cầu theo ba cách. Text Search phù hợp mô tả tự nhiên và ràng buộc. Image Search tìm sản phẩm có đặc trưng thị giác tương tự. Hybrid Search dùng hình ảnh để xác định kiểu dáng và văn bản để bổ sung màu, giá hoặc danh mục. Các nhánh được đưa qua embedding, Qdrant, bộ lọc và tái xếp hạng.

## Slide 19 — Chức năng nổi bật thứ hai

**Thông điệp:** Trợ lý dùng bộ nhớ và retrieval để xử lý câu hỏi tiếp nối có căn cứ.

**Lời dẫn gợi ý (55–65 giây):**

> Trợ lý không xử lý mỗi câu hỏi độc lập. Bộ nhớ khôi phục ràng buộc và lựa chọn trước đó. Với câu hỏi cần dữ liệu sản phẩm, hệ thống thực hiện retrieval rồi lấy thông tin hiện hành trước khi tạo phản hồi. Vì vậy câu hỏi như “mẫu thứ hai còn màu đen không?” vẫn được hiểu đúng trong ngữ cảnh.

## Slide 20 — Chức năng nổi bật thứ ba

**Thông điệp:** Kết quả AI nối trực tiếp vào hành trình đặt hàng và vận hành sau mua.

**Lời dẫn gợi ý (55–65 giây):**

> Sau khi tìm được sản phẩm, khách hàng có thể xem chi tiết, chọn biến thể, kiểm tra giỏ hàng và đặt COD. Backend kiểm tra tồn kho, coupon và địa chỉ trước khi tạo đơn trong transaction. Backoffice tiếp tục xử lý vòng đời đơn hàng và đồng bộ dữ liệu, nên trải nghiệm AI không bị tách khỏi nghiệp vụ thật.

## Slide 21 — Video demo sản phẩm

**Lời dẫn mở video (15–20 giây):**

> Video sau minh họa một luồng xuyên suốt: bắt đầu bằng tìm kiếm văn bản, chuyển sang hình ảnh và kết hợp, tiếp tục hội thoại nhiều lượt, sau đó thêm sản phẩm vào giỏ và hoàn tất đơn COD.

### Timeline video đề xuất

| Thời gian | Nội dung |
|---|---|
| 00:00–00:20 | Mở trang chủ và giới thiệu nhanh hệ thống |
| 00:20–00:50 | Text Search với mô tả tự nhiên và mức giá |
| 00:50–01:20 | Image Search bằng ảnh tham chiếu |
| 01:20–01:55 | Hybrid Search: ảnh kết hợp ràng buộc văn bản |
| 01:55–02:40 | Chat nhiều lượt và câu hỏi tiếp nối |
| 02:40–03:20 | Xem chi tiết, thêm giỏ và đặt hàng COD |
| 03:20–03:40 | Backoffice hoặc đồng bộ chỉ mục AI |

### Nguyên tắc quay

- Quay ở độ phân giải 1920×1080, tỷ lệ 16:9.
- Phóng trình duyệt khoảng 110–125% để chữ dễ đọc trên màn chiếu.
- Không nhập dữ liệu chậm trong video; chuẩn bị sẵn nội dung để dán.
- Cắt thời gian tải dài, nhưng không che giấu kết quả lỗi hoặc làm video thiếu tính liên tục.
- Không dùng nhạc có lời; ưu tiên thuyết minh trực tiếp khi video chạy.
- Chuẩn bị demo trực tiếp và ảnh chụp làm phương án dự phòng.

### Chuyển sang phần kiểm thử

> Video cho thấy hệ thống hoạt động ở góc nhìn người dùng. Phần tiếp theo trình bày cách nhóm kiểm thử và đo lường để xác nhận những kết quả vừa quan sát.
