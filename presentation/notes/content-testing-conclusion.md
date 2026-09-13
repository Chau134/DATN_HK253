# Nội dung thuyết trình — Kiểm thử, kết luận và phụ lục

Thời lượng gợi ý cho slide 22–30: **6–7 phút**. Slide 31 là Q&A, slide 32 là tài liệu tham khảo; không trình bày phụ lục theo thứ tự, chỉ mở trang phù hợp khi hội đồng hỏi.

## Slide 22 — Chiến lược và môi trường kiểm thử

**Thông điệp:** Ba lớp kiểm thử nối kết quả AI với tính đúng đắn của hệ thống và khả năng vận hành.

> Chiến lược gồm ba lớp. Lớp một đánh giá chất lượng AI trên dữ liệu và ground truth đóng băng, trả lời RQ1–RQ2. Lớp hai kiểm thử Backend, hợp đồng dịch vụ, đồng bộ MySQL–Qdrant, năm luồng end-to-end và fallback bằng fixture tái lập, trả lời RQ3. Lớp ba kiểm tra hiệu năng, bảo mật, khả dụng, quan sát và tương thích, trả lời RQ4. Dữ liệu AI gồm 100 truy vấn Text với 2.703 cặp; 100 sản phẩm với 200 ảnh và 2.935 nhãn; 100 truy vấn Hybrid với 1.627 cặp; 80 câu RAG, 120 evidence và 10 phiên dài gồm 230 request. Mọi lượt chạy dùng snapshot 1.000 sản phẩm, MySQL test, Qdrant collection riêng, Redis và lưu manifest, seed, endpoint cùng artifact.

## Slide 23–25 — Tiêu chí, thiết kế so sánh và kết quả chức năng

**Thông điệp:** Cấu hình cuối được chọn theo kết quả thực nghiệm, không mặc định thành phần phức tạp hơn sẽ tốt hơn.

> Hit@5 đo có ít nhất một kết quả đúng trong Top-5; NDCG ưu tiên kết quả đúng ở vị trí cao; MRR đo vị trí kết quả đúng đầu tiên. Trên tập thử thách ngữ nghĩa, Vector không rerank tăng Hit@5 từ 0,756 lên 1,000 và NDCG@5 từ 0,689 lên 0,941 so với BM25. Với Hybrid, Image-conditioned không rerank tăng Strict Hit@5 từ 0,920 của Fusion lên 0,980, Request-conditioned NDCG từ 0,905 lên 0,958 và tỷ lệ thỏa ràng buộc từ 0,779 lên 0,990. Khi bật rerank, Strict Hit@5 giảm còn 0,730 nên cấu hình cuối tắt rerank. Image Search ảnh ngoài đạt Exact Hit@5 0,970; RAG nâng grounding từ 0,824 lên 1,000.

## Slide 26 — Kiểm thử API và tích hợp

**Thông điệp:** Kiểm thử phải đi qua các ranh giới dịch vụ và đối chiếu dữ liệu ở điểm cuối.

> Hệ thống có 26 Spring Controller với 126 request mapping và 14 endpoint FastAPI. Nhóm kiểm tra hợp đồng request–response, full và incremental sync, retry, snapshot, rollback và fallback khi AI lỗi. Hai collection có đủ 1.000 product ID; correlation ID được truyền từ Backend sang AI Service để truy vết một request xuyên hệ thống.

## Slide 27 — Hiệu năng, bảo mật và tương thích

**Thông điệp:** Các gate đã chạy đều đạt, nhưng kết luận chỉ có giá trị trong môi trường thử nghiệm.

> Tải hỗn hợp Backend hoàn tất 6.050 trên 6.050 request. Soak checkout và payment hai giờ hoàn tất 57.600 trên 57.600 request với P95 48,863 mili giây. Các lượt tải AI hoàn tất 360 trên 360 request; P95 Text Search, Hybrid Search và Assistant lần lượt là 1,412; 0,516 và 2,776 giây. Các ca JWT, RBAC, IDOR, injection, XSS và giới hạn request đạt; Playwright đạt 8 trên 8 ca Firefox và WebKit. Kết quả vẫn giới hạn bởi tải AI ngắn, một máy sinh tải, chưa pentest độc lập và chưa xác nhận trình duyệt trên thiết bị thật.

## Slide 28 — Tổng hợp kết quả kiểm thử

**Thông điệp:** Mục tiêu cốt lõi đạt, Image và Hybrid vẫn có giới hạn, hệ thống chưa production-ready.

> Text Search, Hybrid Search, RAG, nghiệp vụ và tích hợp đều đạt các gate đặt ra. Image Search đạt có giới hạn vì có suy giảm trên ảnh bên ngoài dù vẫn vượt ngưỡng nghiệm thu. Toàn hệ thống đạt tiêu chí nghiệm thu nội bộ trong phạm vi đồ án; đây chưa phải chứng nhận sẵn sàng vận hành thương mại.

## Slide 29 — Kết luận: kết quả đã đạt được

**Thông điệp:** Đề tài đã hoàn thành hệ thống thương mại điện tử, năng lực AI, kiến trúc triển khai và kiểm thử theo mục tiêu đặt ra.

> Đề tài đã xây dựng hệ thống thương mại điện tử thời trang cho khách hàng và quản trị viên; hỗ trợ Text, Image và Hybrid Search, YOLOv26, RAG và bộ nhớ hội thoại; tích hợp React, Spring Boot, FastAPI, MySQL và Qdrant; đóng gói Docker, chạy local và triển khai thử nghiệm trên Google Cloud. Các chức năng AI đạt gate, Backend đạt 102/102 ca, hoàn thành năm luồng end-to-end và đồng bộ đủ 1.000 product ID.

## Slide 30 — Hướng phát triển

**Thông điệp kết thúc:** Mở rộng dữ liệu và chất lượng tìm kiếm trước, sau đó củng cố vận hành, bảo mật và trải nghiệm thực tế.

> Hướng phát triển gồm mở rộng sản phẩm, ngành hàng, truy vấn và ảnh thực tế; cải thiện hiểu thuộc tính và xử lý ảnh; cá nhân hóa có quyền kiểm soát dữ liệu; bổ sung thanh toán, vận chuyển, đổi trả và ứng dụng di động; tăng khả năng phục vụ bằng autoscale, hàng đợi và bản sao dữ liệu; đồng thời pentest, diễn tập khôi phục, hoàn thiện dashboard và đánh giá với người dùng thực. Trước mắt ưu tiên mở rộng dữ liệu đánh giá và cải thiện tìm kiếm kết hợp.

## Slide 31 — Q&A

> Nhóm xin cảm ơn hội đồng và sẵn sàng trả lời câu hỏi. Mở đúng phụ lục theo chủ đề được hỏi.

## Slide 32 — Tài liệu tham khảo

Không trình bày nếu không được hỏi. Dùng để truy vết các nguồn ngoài ở slide 3 và slide 7; nguồn số liệu nội bộ nằm trong báo cáo và thư mục đánh giá.

## Cách dùng phụ lục

- **A1 — Ma trận kiểm thử:** khi hỏi số lượng test, quy mô eval hoặc gate.
- **A2 — Hiệu năng:** khi hỏi cấu hình tải, P50/P95/P99 hoặc mức cải thiện.
- **A3 — API:** khi hỏi controller, endpoint hoặc phân chia Spring Boot/FastAPI.
- **A4 — Lỗi đã sửa:** khi hỏi bài học kỹ thuật hoặc bằng chứng kiểm thử tạo ra thay đổi.
- **A5 — YOLOv26s:** khi hỏi dữ liệu fine-tune, Precision/Recall, mAP hoặc vai trò crop ảnh.
- **A6 — Bản đồ bằng chứng:** khi cần mở artifact, báo cáo eval hoặc sơ đồ gốc trong repository.

## Những câu cần tránh nói quá mức

- Không nói hệ thống đã sẵn sàng production.
- Không nói rerank luôn kém; chỉ kết luận không phù hợp với cấu hình và tập thử hiện tại.
- Không nói Image Search chính xác 97% theo mọi nghĩa; con số là Exact Hit@5 trên tập challenging.
- Không gọi WebKit tự động là kiểm thử Safari trên thiết bị thật.
- Không đồng nhất 0 lỗi trong bài tải với hệ thống không có lỗi.
