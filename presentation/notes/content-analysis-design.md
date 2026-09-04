# Nội dung thuyết trình — Phần Phân tích và thiết kế

Tổng thời lượng gợi ý cho slide 9–16: **6–7 phút**. Mục tiêu là giải thích logic thiết kế và các đường biên trách nhiệm; không đọc toàn bộ danh sách yêu cầu hoặc tên công nghệ.

## Slide 9 — Yêu cầu chức năng

**Thông điệp:** 12 yêu cầu AI được đặt trên một hành trình thương mại điện tử gồm 5 năng lực cốt lõi.

**Lời dẫn gợi ý (45–55 giây):**

> Nhóm xác định 17 yêu cầu chức năng. Năm yêu cầu thương mại điện tử tạo hành trình từ tài khoản, khám phá sản phẩm đến đặt và theo dõi đơn hàng. Mười hai yêu cầu AI được nhóm thành tìm kiếm, hiểu truy vấn, hội thoại, xếp hạng, vận hành và dự phòng. Nguyên tắc ưu tiên là tìm đúng, giải thích có căn cứ và không làm gián đoạn nghiệp vụ.

## Slide 10 — Yêu cầu phi chức năng

**Thông điệp:** Hệ thống được thiết kế để đo lường, bảo vệ và vận hành, không chỉ để demo mô hình.

**Lời dẫn gợi ý (50–60 giây):**

> Với quy mô thử nghiệm 500 đến 2.000 sản phẩm và dưới 50 người dùng đồng thời, nhóm đặt mục tiêu 1 đến 3 giây cho nghiệp vụ lõi và 2 đến 5 giây cho tác vụ AI. Chín yêu cầu phi chức năng tập trung vào đúng đắn dữ liệu, khả dụng, bảo trì, tương thích và quan sát hệ thống.

## Slide 11 — Use case tổng quan

**Thông điệp:** Ba tác nhân có ranh giới trách nhiệm rõ ràng.

**Lời dẫn gợi ý (45–55 giây):**

> Khách hàng thực hiện hành trình mua sắm và sử dụng trợ lý. Quản trị viên vận hành dữ liệu cùng đơn hàng và kích hoạt đồng bộ. AI Service là tác nhân hệ thống cung cấp tìm kiếm, chat, xếp hạng và quản lý chỉ mục. Mọi kết quả cuối cùng vẫn đi qua Backend để lấy dữ liệu hiện hành.

## Slide 12 — Kiến trúc tổng thể hệ thống

**Thông điệp:** Frontend chỉ gọi Spring Boot; AI và các kho dữ liệu không lộ trực tiếp ra trình duyệt.

**Lời dẫn gợi ý (60–70 giây):**

> Kiến trúc có một cổng công khai là Spring Boot. Backend xác thực, phân quyền và xử lý nghiệp vụ, sau đó mới gọi AI Service cho các tác vụ tìm kiếm hoặc tư vấn. MySQL giữ dữ liệu nghiệp vụ, Qdrant phục vụ truy hồi vector và checkpoint lưu ngữ cảnh hội thoại. AI chỉ đề xuất định danh; Backend xác nhận giá, tồn kho và dữ liệu trả về.

## Slide 13 — Luồng hoạt động chính

**Thông điệp:** Pipeline AI kết thúc bằng bước xác nhận dữ liệu nghiệp vụ.

**Lời dẫn gợi ý (60–70 giây):**

> Yêu cầu văn bản, hình ảnh và ngữ cảnh được phân tích để trích xuất ý định cùng ràng buộc. Hệ thống tạo embedding, truy hồi Qdrant, hợp nhất và tái xếp hạng ứng viên. Trước khi trả kết quả, Backend đọc giá và tồn kho hiện hành từ MySQL. Bộ nhớ lưu ràng buộc cho lượt tiếp theo; nếu một tín hiệu lỗi, hệ thống có thể sử dụng tín hiệu còn lại.

## Slide 14 — Thiết kế cơ sở dữ liệu

**Thông điệp:** MySQL, Qdrant và Redis không có quyền sở hữu dữ liệu ngang nhau.

**Lời dẫn gợi ý (50–60 giây):**

> Dữ liệu MySQL được chia thành bảy miền nghiệp vụ để giảm phụ thuộc và làm rõ quan hệ. MySQL là nguồn dữ liệu chuẩn cho giao dịch, giá và tồn kho. Qdrant chỉ giữ chỉ mục vector dẫn xuất; Redis giữ cache hoặc checkpoint. Hai kho phục vụ AI có thể tái tạo và không được quyết định trạng thái giao dịch.

## Slide 15 — Công nghệ sử dụng và lý do lựa chọn

**Thông điệp:** Công nghệ được lựa chọn theo vai trò kiến trúc và khả năng thay thế.

**Lời dẫn gợi ý (55–65 giây):**

> React phù hợp giao diện SPA theo component. Spring Boot cung cấp transaction, phân quyền và lớp nghiệp vụ ổn định. FastAPI cùng LangGraph hỗ trợ workflow AI nhiều nhánh và có trạng thái. MySQL, Qdrant và Redis được tách theo đúng loại dữ liệu. Các mô hình managed và Docker giúp cân bằng khả năng triển khai, chi phí và tái lập.

## Slide 16 — Các quyết định kỹ thuật quan trọng

**Thông điệp:** Bốn quyết định tạo ra các đường biên an toàn cho hệ thống.

**Lời dẫn gợi ý (60–70 giây):**

> Bốn quyết định quan trọng gồm: Spring Boot là cổng công khai duy nhất; MySQL là nguồn dữ liệu chuẩn; AI Service được tách và có cơ chế dự phòng; các provider được đóng gói qua adapter và cấu hình. Nhờ vậy AI hỗ trợ quyết định nhưng không nắm quyền thay đổi nghiệp vụ hoặc dữ liệu giao dịch.

## Chuyển sang phần tiếp theo

> Từ kiến trúc và các quyết định trên, nhóm đã hiện thực sản phẩm như thế nào? Phần tiếp theo trình bày các chức năng nổi bật và video demo hệ thống.
