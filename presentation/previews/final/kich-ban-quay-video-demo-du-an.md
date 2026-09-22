# Kịch bản quay video demo không âm thanh — khoảng 3 phút 50 giây

**Đề tài:** Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision  
**Mục đích:** Video chèn tại slide 21, minh họa một hành trình xuyên suốt từ khám phá sản phẩm đến đặt hàng và quản trị.  
**Thời lượng mục tiêu:** 3 phút 40 giây–3 phút 55 giây.  
**Hình thức:** Quay màn hình không âm thanh; giải thích bằng tiêu đề, phụ đề và nhãn ngắn.  
**Định dạng:** MP4, H.264, 1920×1080, 30 fps; không cần audio track.

## 1. Câu chuyện chính

Người dùng đang tìm trang phục nữ để đi làm. Họ tìm bằng mô tả tự nhiên, dùng một ảnh tham khảo để tìm kiểu dáng tương tự, bổ sung ràng buộc bằng văn bản, hỏi tiếp trợ lý trong cùng ngữ cảnh, sau đó chọn sản phẩm, thêm vào giỏ và đặt COD. Cuối video, quản trị viên nhìn thấy đơn hàng vừa tạo trong backoffice.

Video cần làm rõ bốn giá trị của đề tài bằng chữ hiển thị trên màn hình:

1. Đây là một website thương mại điện tử hoàn chỉnh, không chỉ là mô hình AI độc lập.
2. Một giao diện hỗ trợ tìm kiếm bằng văn bản, hình ảnh và kết hợp cả hai.
3. Trợ lý dùng dữ liệu truy hồi và bộ nhớ để hiểu câu hỏi tiếp nối.
4. Kết quả AI nối trực tiếp với nghiệp vụ mua hàng và backoffice.

### Mức độ cần trình bày các chức năng phụ

- **Nên xuất hiện nhanh:** trang chủ, danh mục, bộ lọc, chi tiết sản phẩm, wishlist và blog.
- **Không cần thao tác sâu:** chỉ quay montage 2–4 giây cho mỗi màn hình để chứng minh độ hoàn thiện của sản phẩm.
- **Không cần mở từng trang chính sách:** chỉ lướt nhanh xuống footer để người xem thấy nhóm trang thông tin.
- **Không nên chiếm thời lượng của phần AI:** tổng thời gian cho toàn bộ nhóm chức năng phụ chỉ khoảng 20 giây.

## 2. Chuẩn bị trước khi bấm quay

- Khởi động đầy đủ Frontend, Spring Boot, FastAPI, MySQL, Qdrant và Redis/checkpoint; kiểm tra các dịch vụ ở trạng thái sẵn sàng.
- Mở trình duyệt tại trang chủ, độ phóng 110%; đóng bookmark bar, thông báo và các tab không liên quan.
- Đăng nhập sẵn bằng tài khoản khách hàng có địa chỉ mặc định và quyền đặt hàng.
- Dùng một cửa sổ hoặc browser profile thứ hai đăng nhập sẵn tài khoản quản trị tại `/admin`; chưa đưa cửa sổ này lên màn hình.
- Làm sạch giỏ hàng. Bảo đảm sản phẩm dự kiến chọn còn ít nhất một biến thể có tồn kho.
- Tải trước ảnh kiểm thử ngoài tập dữ liệu và lưu thành `demo-quan-dai.jpg` từ URL sau:
  `https://res.cloudinary.com/dhtlzqflg/image/upload/v1787375985/q2f_hiczuj.png`
- Mở sẵn Notepad chứa các câu để sao chép, nhưng không quay cửa sổ Notepad.
- Chạy thử toàn bộ luồng một lần. Ghi lại tên sản phẩm sẽ chọn, size còn hàng và vị trí của đơn hàng mới nhất.
- Chuẩn bị phần mềm dựng video có thể thêm text box, nền chữ bán trong suốt và hiệu ứng xuất hiện đơn giản.

### Nội dung cần sao chép sẵn

```text
áo sơ mi phù hợp đi làm cho nữ giá 500k đến 1 triệu

tìm váy giống ảnh nhưng đổi sang màu trắng.

Tìm áo sơ mi nữ phù hợp đi làm, giá từ 500 nghìn đến 1 triệu.

Giữ các yêu cầu trên nhưng ưu tiên màu đen.

Trong các mẫu vừa rồi, hãy so sánh hai mẫu đầu tiên và gợi ý mẫu phù hợp hơn để đi làm.
```

## 3. Kịch bản chi tiết theo thời gian

Các câu trong cột **Chữ trên video** là nội dung để chèn khi dựng, không phải lời đọc. Nếu một ô có hai câu, cho chúng xuất hiện lần lượt, không hiển thị cùng lúc.

| Thời gian | Hình ảnh và thao tác | Chữ trên video |
|---:|---|---|
| **00:00–00:10** | Hiện trang chủ và banner chính. | Tiêu đề giữa màn hình: **TRỢ LÝ MUA SẮM ĐA PHƯƠNG TIỆN**<br>Dòng nhỏ: *Từ khám phá sản phẩm đến hoàn tất đơn hàng* |
| **00:10–00:30** | Montage cắt nhanh: trang chủ → danh mục và bộ lọc → chi tiết một sản phẩm → thêm/bỏ wishlist → trang blog → lướt nhanh xuống footer có các trang thông tin. Mỗi cảnh khoảng 3 giây, không nhập liệu. | Nhãn góc trên: **NỀN TẢNG THƯƠNG MẠI ĐIỆN TỬ**<br>Phụ đề 1: *Danh mục • Bộ lọc • Chi tiết sản phẩm • Wishlist*<br>Phụ đề 2: *Blog và các trang thông tin hỗ trợ khách hàng* |
| **00:30–00:53** | Mở `/tu-van`. Tại **Tìm theo từ khóa**, dán câu `áo sơ mi phù hợp đi làm cho nữ giá 500k đến 1 triệu`, bấm **Tìm**, chờ lưới kết quả rồi rê chuột chậm qua 2–3 thẻ sản phẩm. | Nhãn góc trên: **1. TEXT SEARCH**<br>Phụ đề 1: *Tìm bằng mô tả tự nhiên và các điều kiện cụ thể*<br>Phụ đề 2: *Hiểu danh mục • mục đích • giới tính • khoảng giá* |
| **00:53–01:15** | Tại **Tìm bằng ảnh**, chọn `demo-quan-dai.jpg`. Dừng để các khung phát hiện của YOLO xuất hiện. Giữ vùng sản phẩm phù hợp được chọn rồi bấm **Tìm**. | Nhãn góc trên: **2. IMAGE SEARCH**<br>Phụ đề 1: *YOLO tự động phát hiện vùng sản phẩm trong ảnh*<br>Phụ đề 2: *Tìm các sản phẩm tương đồng về thị giác* |
| **01:15–01:40** | Tại **Tìm kết hợp**, dùng lại `demo-quan-dai.jpg`; dán `tìm quần dài giống ảnh, giá từ 500k đến 1 triệu`; giữ vùng YOLO và bấm **Tìm**. Khi có kết quả, trỏ vào mức giá và ảnh của vài sản phẩm. | Nhãn góc trên: **3. HYBRID SEARCH**<br>Phụ đề 1: *Hình ảnh xác định kiểu dáng*<br>Phụ đề 2: *Văn bản bổ sung danh mục và ngân sách*<br>Phụ đề 3: *Kết quả vừa giống ảnh, vừa đúng nhu cầu* |
| **01:40–01:50** | Mở biểu tượng **Trợ lý mua sắm** ở góc màn hình và mở rộng cửa sổ chat nếu cần. | Tiêu đề ngắn giữa màn hình: **TRỢ LÝ AI ĐA LƯỢT**<br>Dòng nhỏ: *RAG + Bộ nhớ hội thoại* |
| **01:50–02:09** | Gửi: `Tìm áo sơ mi nữ phù hợp đi làm, giá từ 500 nghìn đến 1 triệu.` Chờ câu trả lời và danh sách sản phẩm. Cuộn vừa đủ để thấy phản hồi cùng 2–3 thẻ sản phẩm. | Phụ đề 1: *Lượt 1: phân tích nhu cầu và truy hồi sản phẩm*<br>Phụ đề 2: *Giá, biến thể và tồn kho được lấy từ Backend* |
| **02:09–02:25** | Gửi tiếp: `Giữ các yêu cầu trên nhưng ưu tiên màu đen.` Dừng ở phần chip/ràng buộc và kết quả mới. | Phụ đề 1: *Lượt 2: không cần nhập lại yêu cầu trước đó*<br>Phụ đề 2: *Bộ nhớ giữ ngữ cảnh và bổ sung “màu đen”* |
| **02:25–02:40** | Gửi: `Trong các mẫu vừa rồi, hãy so sánh hai mẫu đầu tiên và gợi ý mẫu phù hợp hơn để đi làm.` Giữ màn hình ở phần phản hồi so sánh. | Phụ đề 1: *Lượt 3: hiểu tham chiếu “hai mẫu đầu tiên”*<br>Phụ đề 2: *So sánh dựa trên dữ liệu đã truy hồi* |
| **02:40–02:58** | Bấm vào một sản phẩm còn hàng trong kết quả. Ở trang chi tiết, chỉ vào giá và tồn kho; chọn size đã thử trước rồi bấm **Thêm vào giỏ hàng**. Mở **Giỏ hàng**. | Nhãn góc trên: **4. TỪ TƯ VẤN ĐẾN MUA HÀNG**<br>Phụ đề 1: *Chọn sản phẩm và biến thể còn hàng*<br>Phụ đề 2: *Backend xác nhận giá và tồn kho thực tế* |
| **02:58–03:20** | Tại giỏ hàng, bấm **Tiến hành thanh toán**. Trang checkout đã có sẵn thông tin giao hàng; chọn **Thanh toán khi nhận hàng (COD)**, đánh dấu chấp nhận điều khoản và bấm **Thanh Toán Khi Nhận Hàng**. | Phụ đề 1: *Kiểm tra giỏ hàng • địa chỉ • coupon • tồn kho*<br>Phụ đề 2: *Hoàn tất đơn hàng bằng phương thức COD* |
| **03:20–03:31** | Dừng ở trang **Cảm ơn bạn đã đặt hàng!**, trỏ chuột vào mã đơn và trạng thái thanh toán COD. | Chữ xác nhận giữa màn hình: **ĐẶT HÀNG THÀNH CÔNG**<br>Dòng nhỏ: *Có mã giao dịch và trạng thái theo dõi* |
| **03:31–03:45** | Chuyển sang cửa sổ quản trị đã mở sẵn, chọn **Đơn Hàng**, đưa đơn vừa tạo vào khung hình. Không cần bấm xác nhận COD. | Nhãn góc trên: **5. BACKOFFICE**<br>Phụ đề: *Đơn hàng vừa tạo xuất hiện trong hệ thống quản trị* |
| **03:45–03:52** | Làm mờ nhẹ màn hình backoffice và hiện khung kết. | Chữ giữa màn hình: **AI ĐƯỢC TÍCH HỢP XUYÊN SUỐT HÀNH TRÌNH MUA SẮM** |

## 4. Lời mở và lời kết khi trình chiếu slide 21

**Lời mở trước khi phát video:**

> Video sau minh họa một hành trình xuyên suốt: tìm kiếm bằng văn bản, tìm bằng ảnh, kết hợp ảnh với ràng buộc văn bản, hội thoại nhiều lượt, sau đó thêm sản phẩm vào giỏ, đặt COD và kiểm tra đơn ở backoffice.

**Lời kết sau video:**

> Demo cho thấy AI không hoạt động như một chức năng tách rời, mà được tích hợp vào toàn bộ hành trình mua sắm. Tiếp theo, em trình bày cách hệ thống được kiểm thử và các kết quả định lượng đạt được.

## 5. Chỉ dẫn dựng video

- Cắt các khoảng chờ API dài hơn 2 giây; có thể tăng tốc đoạn chờ 1,5–2 lần nhưng không cắt mất trạng thái **Đang xử lý** hoặc **Đang trả lời**.
- Video giữ hoàn toàn im lặng, không cần nhạc nền hoặc hiệu ứng âm thanh.
- Dùng chuyển cảnh cắt thẳng. Không dùng hiệu ứng phức tạp hoặc zoom giật.
- Khi cần nhấn mạnh, chỉ phóng nhẹ vào vùng kết quả, chip ràng buộc, giá/tồn kho, thông báo đặt hàng thành công và đơn hàng trong backoffice.
- Phụ đề đặt ở vùng dưới màn hình, nền đen bán trong suốt khoảng 65–75%; tránh che nút đang bấm và thông tin sản phẩm.
- Mỗi phụ đề tối đa hai dòng, khoảng 8–12 từ mỗi dòng; dùng cỡ chữ tương đương 32–40 px ở video Full HD.
- Dùng chữ trắng; chỉ tô xanh ngọc hoặc cam cho từ khóa như **YOLO**, **RAG**, **Bộ nhớ**, **COD**.
- Giữ mỗi phụ đề ít nhất 3 giây. Với đoạn có nhiều phụ đề, cho xuất hiện lần lượt bằng hiệu ứng fade nhẹ 0,2–0,3 giây.
- Nhãn tên chức năng đặt cố định ở góc trên bên trái và nhỏ hơn phụ đề chính.
- Che email, số điện thoại, địa chỉ, token và dữ liệu cá nhân nếu tài khoản demo dùng thông tin thật.
- Không hiển thị DevTools, log lỗi, khóa API hoặc file `.env` trong video.
- Giữ con trỏ ổn định; sau mỗi lần bấm, dừng 1 giây để người xem nhận biết kết quả.
- Xuất file cuối cùng thành `presentation/assets/video/demo-san-pham.mp4`.

## 6. Phương án dự phòng

- Nếu LLM phản hồi chậm, quay riêng từng phân đoạn rồi ghép theo timeline; vẫn giữ một lượt hiển thị trạng thái đang xử lý để bảo đảm tính trung thực.
- Nếu Image/Hybrid Search không ổn định, dùng đúng ảnh `demo-quan-dai.jpg` và câu truy vấn đã nêu vì đây là một ca đã được duyệt trong bộ đánh giá của dự án.
- Nếu câu so sánh không cho kết quả đẹp, dừng ở hai lượt đầu của hội thoại và dành thêm 10–15 giây cho trang chi tiết sản phẩm.
- Nếu đặt hàng lỗi do hết tồn kho, chọn sản phẩm và size dự phòng đã xác nhận trước khi quay; không sửa dữ liệu giữa video.
- Nếu không thể chuyển nhanh sang tài khoản quản trị, kết thúc ở trang đặt hàng thành công. Phần backoffice là bằng chứng bổ sung, không nên làm hỏng nhịp chính.

## 7. Checklist nghiệm thu video

- [ ] Độ dài không vượt quá 3 phút 55 giây.
- [ ] Có montage ngắn giới thiệu danh mục, chi tiết sản phẩm, wishlist, blog và footer thông tin.
- [ ] Nhìn rõ đủ ba chế độ Text, Image và Hybrid Search.
- [ ] Thấy vùng ảnh do YOLO phát hiện hoặc vùng crop do người dùng chọn.
- [ ] Có ít nhất hai lượt chat liên tiếp thể hiện việc giữ ngữ cảnh.
- [ ] Có thao tác chọn biến thể, thêm giỏ, checkout COD và trang thành công.
- [ ] Nếu có backoffice, đơn hàng trên màn hình đúng là đơn vừa tạo.
- [ ] Không lộ thông tin cá nhân, credential hoặc dữ liệu kỹ thuật nhạy cảm.
- [ ] Video không có âm thanh và không xuất hiện khoảng trống khó hiểu giữa các thao tác.
- [ ] Mọi phụ đề đều đọc hết được trước khi chuyển cảnh và không che nội dung quan trọng.
- [ ] File cuối cùng phát bình thường trong PowerPoint trên máy dùng để bảo vệ.
