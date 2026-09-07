# Nội dung thuyết trình — Kiểm thử, kết luận và phụ lục

Thời lượng gợi ý cho slide 22–30: **6–7 phút**. Không trình bày phụ lục theo thứ tự; chỉ mở trang phù hợp khi hội đồng hỏi.

## Slide 22 — Chiến lược và môi trường kiểm thử

**Thông điệp:** Chất lượng AI và tính đúng của hệ thống được kiểm chứng như hai lớp độc lập.

> Nhóm chia đánh giá thành hai lớp. Lớp AI đo chất lượng truy hồi, RAG và bộ nhớ bằng baseline, ablation cùng ground truth đã duyệt. Lớp hệ thống kiểm tra nghiệp vụ, tích hợp, end-to-end và các thuộc tính phi chức năng. Mọi lần chạy dùng snapshot 1.000 sản phẩm, schema và collection riêng, seed cùng manifest có thể truy vết.

## Slide 23–25 — Tiêu chí, thiết kế so sánh và kết quả chức năng

**Thông điệp:** Cấu hình cuối được chọn theo kết quả thực nghiệm, không mặc định thành phần phức tạp hơn sẽ tốt hơn.

> Text Search không rerank đạt Hit@5 bằng 1,000. Image Search đạt Exact Hit@5 bằng 0,970 trên ảnh thử thách. Hybrid fusion không rerank đạt Strict Hit@5 bằng 0,920, nhưng tỷ lệ thỏa đồng thời mọi ràng buộc trong Top-5 chỉ đạt 0,450. RAG kết hợp memory đạt grounding 1,000. Ngoài AI, 102 trên 102 ca Backend và 430 ca hồi quy AI đều đạt.

## Slide 26 — Kiểm thử API và tích hợp

**Thông điệp:** Kiểm thử phải đi qua các ranh giới dịch vụ và đối chiếu dữ liệu ở điểm cuối.

> Hệ thống có 26 Spring Controller với 126 request mapping và 14 endpoint FastAPI. Nhóm kiểm tra hợp đồng request–response, full và incremental sync, retry, snapshot, rollback và fallback khi AI lỗi. Hai collection có đủ 1.000 product ID; correlation ID được truyền từ Backend sang AI Service để truy vết một request xuyên hệ thống.

## Slide 27 — Hiệu năng, bảo mật và tương thích

**Thông điệp:** Các gate đã chạy đều đạt, nhưng kết luận chỉ có giá trị trong môi trường thử nghiệm.

> Tải Backend hoàn tất 21.231 trên 21.231 request. Soak checkout và payment hai giờ hoàn tất 57.600 trên 57.600 request với P95 48,863 mili giây. Tải AI đồng thời hoàn tất 216 trên 216 request; P95 Text Search, Hybrid Search và Assistant lần lượt là 1,412; 3,412 và 2,776 giây. Các ca JWT, RBAC, IDOR, injection, XSS và giới hạn request đạt; Playwright đạt 8 trên 8 ca Firefox và WebKit. Kết quả vẫn giới hạn bởi tải AI ngắn, một máy sinh tải, chưa pentest độc lập và chưa xác nhận Safari thật.

## Slide 28 — Tổng hợp kết quả kiểm thử

**Thông điệp:** Mục tiêu cốt lõi đạt, Image và Hybrid vẫn có giới hạn, hệ thống chưa production-ready.

> Text Search, RAG, nghiệp vụ và tích hợp đạt các gate đặt ra. Image Search đạt có giới hạn; Hybrid Search đạt một phần vì tỷ lệ thỏa đồng thời mọi ràng buộc trong Top-5 mới đạt 0,450. Toàn hệ thống đạt tiêu chí nghiệm thu nội bộ trong phạm vi đồ án; đây chưa phải chứng nhận sẵn sàng vận hành thương mại.

## Slide 29 — Hạn chế và hướng phát triển

**Thông điệp:** Ưu tiên củng cố bằng chứng và vận hành trước khi mở rộng tính năng.

> Các giới hạn chính nằm ở benchmark chưa hoàn toàn held-out, Hybrid Search chưa giữ đủ ràng buộc, BM25 chưa đo latency, so sánh P95 rerank chưa paired và tải AI mới kéo dài ba phút. Assistant còn P99 9,704 giây. Hướng ưu tiên là hoàn thiện constraint của Hybrid Search, xây dựng benchmark held-out, chạy tải dài và paired đầy đủ, rồi pentest và đánh giá trên thiết bị thật.

## Slide 30 — Kết luận và Q&A

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
