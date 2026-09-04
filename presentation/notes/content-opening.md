# Nội dung thuyết trình — Phần Mở đầu và bài toán

Tổng thời lượng gợi ý cho 8 slide: **5–6 phút**. Phần này cần tạo động lực và định vị đóng góp; chưa đi sâu vào công nghệ.

## Slide 1 — Trang bìa

**Thông điệp:** Giới thiệu đề tài, nhóm thực hiện và phạm vi AI trung tâm.

**Lời dẫn gợi ý (20–30 giây):**

> Kính thưa hội đồng, nhóm em xin trình bày đề tài “Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision”. Đề tài tập trung xây dựng một hệ thống thương mại điện tử hoàn chỉnh, trong đó người dùng có thể tìm kiếm và nhận tư vấn bằng văn bản, hình ảnh và hội thoại nhiều lượt.

## Slide 2 — Nội dung trình bày

**Thông điệp:** Bài trình bày đi từ nhu cầu thực tế tới giải pháp, sản phẩm và bằng chứng đánh giá.

**Lời dẫn gợi ý (20 giây):**

> Phần trình bày gồm năm nội dung. Nhóm bắt đầu từ bài toán, tiếp theo là phân tích và thiết kế, sản phẩm cùng video demo, phần kiểm thử và đánh giá, cuối cùng là kết luận.

## Slide 3 — Bối cảnh và lý do chọn đề tài

**Thông điệp:** Ý định mua sắm xuất hiện đồng thời dưới dạng văn bản, hình ảnh và ngữ cảnh hội thoại.

**Lời dẫn gợi ý (45–55 giây):**

> Trong thực tế, khách hàng hiếm khi chỉ nhớ đúng tên sản phẩm. Họ có thể mô tả nhu cầu tự nhiên, đưa một ảnh tham chiếu, rồi tiếp tục hỏi về màu, size hoặc mức giá. Vì vậy, hệ thống cần hiểu và kết nối cả ba loại tín hiệu thay vì xử lý chúng như các kênh rời rạc.

## Slide 4 — Bài toán thực tế

**Thông điệp:** Có ba điểm gãy: khoảng cách ngữ nghĩa, khoảng cách thị giác và mất ngữ cảnh.

**Lời dẫn gợi ý (50–60 giây):**

> Nhóm xác định ba vấn đề chính. Thứ nhất, từ khóa không biểu đạt hết ý định. Thứ hai, ảnh khó chuyển thành các thuộc tính truy vấn. Thứ ba, câu hỏi tiếp nối phụ thuộc vào ngữ cảnh ở lượt trước. Hệ quả là hệ thống có thể trả về rất nhiều kết quả nhưng người dùng vẫn mất thời gian để tìm lựa chọn phù hợp.

## Slide 5 — Mục tiêu đề tài

**Thông điệp:** Mục tiêu bao phủ cả năng lực AI, tích hợp hệ thống và đánh giá.

**Lời dẫn gợi ý (45–55 giây):**

> Từ bài toán trên, nhóm đặt ra bốn mục tiêu: hỗ trợ ba chế độ tìm kiếm; tạo tư vấn có căn cứ bằng RAG và bộ nhớ; tích hợp AI vào toàn bộ hệ thống thương mại điện tử; và đánh giá bằng các chỉ số chất lượng, độ trễ cùng kiểm thử hệ thống.

## Slide 6 — Phạm vi và đối tượng sử dụng

**Thông điệp:** Đây là nguyên mẫu thời trang phục vụ khách hàng và quản trị viên, với ranh giới rõ ràng.

**Lời dẫn gợi ý (45–55 giây):**

> Hệ thống phục vụ hai nhóm người dùng. Khách hàng thực hiện hành trình từ khám phá đến theo dõi đơn; quản trị viên vận hành danh mục và nghiệp vụ. Đề tài tập trung vào tìm kiếm, tư vấn, đồng bộ dữ liệu và web thương mại điện tử. Thanh toán thật, vận chuyển và hạ tầng thương mại quy mô lớn nằm ngoài phạm vi.

## Slide 7 — Khảo sát các giải pháp liên quan

**Thông điệp:** Các nhóm giải pháp phổ biến thường tối ưu một năng lực; khoảng trống là tích hợp xuyên suốt.

**Lời dẫn gợi ý (55–65 giây):**

> Khi khảo sát theo nhóm năng lực, tìm kiếm truyền thống mạnh ở bộ lọc nghiệp vụ nhưng hạn chế về ngữ nghĩa. Tìm kiếm ảnh giải quyết tín hiệu thị giác. Chatbot LLM hỗ trợ giao tiếp nhưng nếu tách khỏi dữ liệu sản phẩm thì khó bảo đảm căn cứ. Giải pháp đề xuất kết nối các năng lực này với nghiệp vụ thương mại điện tử.

**Lưu ý khi bảo vệ:** Các ký hiệu trong bảng thể hiện mức độ đáp ứng tương đối theo trọng tâm của từng nhóm giải pháp, không phải kết quả benchmark giữa các sản phẩm thương mại.

## Slide 8 — Điểm khác biệt của giải pháp

**Thông điệp:** Giá trị nằm ở vòng lặp end-to-end và bằng chứng kiểm chứng, không chỉ ở việc gọi một mô hình AI.

**Lời dẫn gợi ý (55–65 giây):**

> Điểm khác biệt của đề tài là đặt AI trong một vòng lặp mua sắm hoàn chỉnh: hiểu tín hiệu, truy hồi với ràng buộc, tư vấn có căn cứ, rồi đưa người dùng về hành động mua hàng. AI Service được tách khỏi nghiệp vụ lõi để hỗ trợ dự phòng, và toàn bộ giải pháp được đánh giá bằng baseline, ablation, chỉ số truy hồi, độ trễ và kiểm thử hệ thống.

## Chuyển sang phần tiếp theo

> Sau khi xác định bài toán, mục tiêu và phạm vi, nhóm xin trình bày các yêu cầu và cách thiết kế hệ thống để hiện thực hóa giải pháp này.
