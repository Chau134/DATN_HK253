# Nội dung thuyết trình — Kiểm thử, kết luận và phụ lục

Thời lượng gợi ý cho slide 22–27: **4 phút**. Slide 28 là Q&A, slide 29 là tài liệu tham khảo; không trình bày phụ lục theo thứ tự, chỉ mở trang phù hợp khi hội đồng hỏi.

## Slide 22 — Phạm vi kiểm thử

**Thông điệp:** Ba lớp kiểm thử nối kết quả AI với tính đúng đắn của hệ thống và khả năng vận hành.

> Kiểm thử gồm ba lớp. Lớp một đánh giá Text, Image, Hybrid Search cùng RAG và memory. Lớp hai kiểm tra API, nghiệp vụ, đồng bộ MySQL–Qdrant, end-to-end và xử lý lỗi. Lớp ba đánh giá hiệu năng, độ ổn định, bảo mật và tương thích. Cả ba lớp dùng snapshot, fixture, seed, gate và artifact để bảo đảm khả năng tái lập.

## Slide 23 — Quy trình kiểm thử

**Thông điệp:** Ba lớp dùng chung dữ liệu kiểm soát nhưng có cách thực thi và bằng chứng khác nhau.

> AI đi từ ground truth qua baseline và ablation, đo metric rồi chọn cấu hình. Chức năng và tích hợp đi từ test case qua API và end-to-end, đối chiếu dữ liệu rồi kiểm tra retry, rollback và fallback. Phi chức năng đi từ workload và rủi ro qua load, security và browser, thu P95 cùng lỗi rồi đánh giá giới hạn. Đầu ra được phân loại đạt, đạt có giới hạn hoặc chưa đạt.

## Slide 24 — Kết quả kiểm thử chính

**Thông điệp:** Ba nhóm chính đều đạt tiêu chí, nhưng kết luận phi chức năng chỉ có giá trị trong phạm vi thử nghiệm.

> AI nổi bật với Text Hit@5 bằng 1,000, Hybrid Strict Hit@5 bằng 0,980 và RAG Grounding bằng 1,000; Image Search trên ảnh ngoài đạt 0,970 nhưng còn giới hạn. Chức năng và tích hợp đạt 102/102 ca nghiệp vụ, 5/5 luồng end-to-end, đồng bộ đủ 1.000 product ID và đạt các ca retry, rollback, fallback. Phi chức năng hoàn tất 57.600/57.600 request soak hai giờ, P95 Catalog–Cart 182,79 mili giây, các gate bảo mật và 8/8 ca Firefox–WebKit đều đạt trong phạm vi thử.

## Slide 25 — Tổng hợp kết quả kiểm thử

**Thông điệp:** Các gate đã chạy đều đạt, nhưng kết luận chỉ có giá trị trong môi trường thử nghiệm.

**Thông điệp:** Mục tiêu cốt lõi đạt, Image vẫn có giới hạn, hệ thống chưa production-ready.

> Text Search, Hybrid Search, RAG, nghiệp vụ và tích hợp đều đạt các gate đặt ra. Image Search đạt có giới hạn vì có suy giảm trên ảnh bên ngoài dù vẫn vượt ngưỡng nghiệm thu. Toàn hệ thống đạt tiêu chí nghiệm thu nội bộ trong phạm vi đồ án; đây chưa phải chứng nhận sẵn sàng vận hành thương mại.

## Slide 26 — Kết luận: kết quả đã đạt được

**Thông điệp:** Đề tài đã hoàn thành hệ thống thương mại điện tử, năng lực AI, kiến trúc triển khai và kiểm thử theo mục tiêu đặt ra.

> Đề tài đã xây dựng hệ thống thương mại điện tử thời trang cho khách hàng và quản trị viên; hỗ trợ Text, Image và Hybrid Search, YOLOv26, RAG và bộ nhớ hội thoại; tích hợp React, Spring Boot, FastAPI, MySQL và Qdrant; đóng gói Docker, chạy local và triển khai thử nghiệm trên Google Cloud. Các chức năng AI đạt gate, Backend đạt 102/102 ca, hoàn thành năm luồng end-to-end và đồng bộ đủ 1.000 product ID.

## Slide 27 — Hướng phát triển

**Thông điệp kết thúc:** Mở rộng dữ liệu và chất lượng tìm kiếm trước, sau đó củng cố vận hành, bảo mật và trải nghiệm thực tế.

> Hướng phát triển gồm mở rộng sản phẩm, ngành hàng, truy vấn và ảnh thực tế; cải thiện hiểu thuộc tính và xử lý ảnh; cá nhân hóa có quyền kiểm soát dữ liệu; bổ sung thanh toán, vận chuyển, đổi trả và ứng dụng di động; tăng khả năng phục vụ bằng autoscale, hàng đợi và bản sao dữ liệu; đồng thời pentest, diễn tập khôi phục, hoàn thiện dashboard và đánh giá với người dùng thực. Trước mắt ưu tiên mở rộng dữ liệu đánh giá và cải thiện tìm kiếm kết hợp.

## Slide 28 — Q&A

> Nhóm xin cảm ơn hội đồng và sẵn sàng trả lời câu hỏi. Mở đúng phụ lục theo chủ đề được hỏi.

## Slide 29 — Tài liệu tham khảo

Không trình bày nếu không được hỏi. Dùng để truy vết các nguồn ngoài ở slide 3 và slide 7; nguồn số liệu nội bộ nằm trong báo cáo và thư mục đánh giá.

## Cách dùng phụ lục

- **A1 — Ma trận kiểm thử:** khi hỏi số lượng test, quy mô eval hoặc gate.
- **A2 — Hiệu năng:** khi hỏi cấu hình tải, P50/P95/P99 hoặc mức cải thiện.
- **A3 — API:** khi hỏi controller, endpoint hoặc phân chia Spring Boot/FastAPI.
- **A4 — Lỗi đã sửa:** khi hỏi bài học kỹ thuật hoặc bằng chứng kiểm thử tạo ra thay đổi.
- **A5 — YOLOv26s:** khi hỏi dữ liệu fine-tune, Precision/Recall, mAP hoặc vai trò crop ảnh.
- **A6 — Bản đồ bằng chứng:** khi cần mở artifact, báo cáo eval hoặc sơ đồ gốc trong repository.
- **A7 — Thiết kế đánh giá AI:** khi hỏi ground truth, phép so sánh, metric hoặc gate.
- **A8 — Baseline và ablation:** khi hỏi lý do chọn Vector, Image-conditioned hoặc tắt rerank.
- **A9 — Tích hợp và phi chức năng:** khi hỏi số liệu API, đồng bộ, URL ảnh, hiệu năng, bảo mật hoặc trình duyệt.

## Những câu cần tránh nói quá mức

- Không nói hệ thống đã sẵn sàng production.
- Không nói rerank luôn kém; chỉ kết luận không phù hợp với cấu hình và tập thử hiện tại.
- Không nói Image Search chính xác 97% theo mọi nghĩa; con số là Exact Hit@5 trên tập challenging.
- Không gọi WebKit tự động là kiểm thử Safari trên thiết bị thật.
- Không đồng nhất 0 lỗi trong bài tải với hệ thống không có lỗi.
