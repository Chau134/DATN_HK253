# Nội dung thuyết trình — Kiểm thử, kết luận và phụ lục

Thời lượng gợi ý cho slide 22–28: **6–7 phút**. Không trình bày phụ lục theo thứ tự; chỉ mở trang phù hợp khi hội đồng hỏi.

## Slide 22 — Chiến lược và môi trường kiểm thử

**Thông điệp:** Chất lượng AI và tính đúng của hệ thống được kiểm chứng như hai lớp độc lập.

> Nhóm chia đánh giá thành hai lớp. Lớp AI đo chất lượng truy hồi, RAG và bộ nhớ bằng baseline, ablation cùng ground truth đã duyệt. Lớp hệ thống kiểm tra nghiệp vụ, tích hợp, end-to-end và các thuộc tính phi chức năng. Mọi lần chạy dùng snapshot 1.000 sản phẩm, schema và collection riêng, seed cùng manifest có thể truy vết.

## Slide 23 — Kiểm thử chức năng

**Thông điệp:** Cấu hình cuối được chọn theo kết quả thực nghiệm, không mặc định thành phần phức tạp hơn sẽ tốt hơn.

> Text Search không rerank đạt Hit@5 bằng 1,000. Image Search đạt Hit@5 bằng 0,970 trên ảnh thử thách. Hybrid fusion không rerank đạt Strict Hit@5 bằng 0,920, nhưng tỷ lệ trung bình thỏa toàn bộ ràng buộc mới đạt 0,446. RAG kết hợp memory đạt grounding 1,000. Ngoài AI, 102 trên 102 ca Backend và 430 ca hồi quy AI đều đạt.

## Slide 24 — Kiểm thử API và tích hợp

**Thông điệp:** Kiểm thử phải đi qua các ranh giới dịch vụ và đối chiếu dữ liệu ở điểm cuối.

> Hệ thống có 26 Spring Controller với 126 request mapping và 14 endpoint FastAPI. Nhóm kiểm tra hợp đồng request–response, full và incremental sync, retry, snapshot, rollback và fallback khi AI lỗi. Hai collection có đủ 1.000 product ID; correlation ID được truyền từ Backend sang AI Service để truy vết một request xuyên hệ thống.

## Slide 25 — Hiệu năng, bảo mật và khả năng sử dụng

**Thông điệp:** Các gate đã chạy đều đạt, nhưng kết luận chỉ có giá trị trong môi trường thử nghiệm.

> Ba bài tải hoàn tất 21.231 request mà không lỗi. Sau tối ưu, P95 tải hỗn hợp giảm 73,6 phần trăm xuống 182,79 mili giây. Các ca JWT, RBAC, IDOR, injection, XSS và giới hạn request đạt. Playwright đạt 8 trên 8 ca Firefox và WebKit. Tuy nhiên, nhóm chưa chạy tải AI đồng thời, soak dài hạn, pentest độc lập, Safari thật hoặc SUS với người dùng.

## Slide 26 — Tổng hợp kết quả kiểm thử

**Thông điệp:** Mục tiêu cốt lõi đạt, Image và Hybrid vẫn có giới hạn, hệ thống chưa production-ready.

> Text Search, RAG, nghiệp vụ và tích hợp đạt các gate đặt ra. Image Search đạt nhưng giảm chất lượng trên ảnh thực tế. Hybrid Search đạt Strict Hit@5 nhưng chưa giữ nghiêm tất cả ràng buộc trong Top-5. Vì vậy, đề tài chứng minh tính khả thi kỹ thuật và giá trị tích hợp, chưa tuyên bố sẵn sàng vận hành thương mại.

## Slide 27 — Hạn chế và hướng phát triển

**Thông điệp:** Ưu tiên củng cố bằng chứng và vận hành trước khi mở rộng tính năng.

> Bốn hạn chế chính là quy mô dữ liệu, độ bền truy hồi, độ bao phủ kiểm thử phi chức năng và thiếu đánh giá người dùng thật. Hướng ưu tiên là mở rộng tập held-out và ảnh người dùng, tách hard filter trong Hybrid Search, chạy tải dài hạn và pentest, sau đó mới mở rộng indexing hướng sự kiện, thanh toán và vận chuyển.

## Slide 28 — Kết luận và Q&A

**Thông điệp kết thúc:** AI hỗ trợ quyết định; dữ liệu nghiệp vụ giữ quyền kiểm soát.

> Đề tài đóng góp một hệ thống end-to-end, một kiến trúc có đường biên trách nhiệm rõ ràng và một quy trình đánh giá bằng baseline, ablation cùng kiểm thử hệ thống. Nhóm xin cảm ơn hội đồng và sẵn sàng trả lời câu hỏi.

## Cách dùng phụ lục

- **A1 — Ma trận kiểm thử:** khi hỏi số lượng test, quy mô eval hoặc gate.
- **A2 — Hiệu năng:** khi hỏi cấu hình tải, P50/P95/P99 hoặc mức cải thiện.
- **A3 — ERD:** khi hỏi quan hệ bảng, khóa hoặc miền dữ liệu.
- **A4 — API:** khi hỏi controller, endpoint hoặc phân chia Spring Boot/FastAPI.
- **A5 — Lỗi đã sửa:** khi hỏi bài học kỹ thuật hoặc bằng chứng kiểm thử tạo ra thay đổi.
- **A6 — Bản đồ bằng chứng:** khi cần mở artifact, báo cáo eval hoặc sơ đồ gốc trong repository.

## Những câu cần tránh nói quá mức

- Không nói hệ thống đã sẵn sàng production.
- Không nói rerank luôn kém; chỉ kết luận không phù hợp với cấu hình và tập thử hiện tại.
- Không nói Image Search chính xác 97% theo mọi nghĩa; con số là Exact Hit@5 trên tập challenging.
- Không gọi WebKit tự động là kiểm thử Safari trên thiết bị thật.
- Không đồng nhất 0 lỗi trong bài tải với hệ thống không có lỗi.
