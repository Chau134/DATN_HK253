# Nội dung thuyết trình — Kiểm thử, kết luận và phụ lục

Thời lượng gợi ý cho slide 22–30: **6–7 phút**. Slide 31 là Q&A, slide 32 là tài liệu tham khảo; không trình bày phụ lục theo thứ tự, chỉ mở trang phù hợp khi hội đồng hỏi.

## Slide 22 — Dữ liệu và cấu hình đánh giá

**Thông điệp:** Mọi kết quả dùng cùng dữ liệu đóng băng, nhãn có provenance và biên đo có thể tái lập.

> Dữ liệu bắt đầu từ snapshot 1.000 sản phẩm trong MySQL. Text Search có 2.703 nhãn; Image Search có 2.935 nhãn kết hợp duyệt thị giác và luật metadata; Hybrid có 654 nhãn duyệt thủ công; RAG có 80 bộ question--reference--evidence đã duyệt. Các lần chạy giữ nguyên snapshot, model, prompt và collection, kiểm tra readiness, lưu manifest cùng run ID. Độ trễ được đo end-to-end ở client; bootstrap dùng 10.000 mẫu và seed 42.

## Slide 23–25 — Tiêu chí, thiết kế so sánh và kết quả chức năng

**Thông điệp:** Cấu hình cuối được chọn theo kết quả thực nghiệm, không mặc định thành phần phức tạp hơn sẽ tốt hơn.

> Hit@5 đo có ít nhất một kết quả đúng trong Top-5; NDCG ưu tiên kết quả đúng ở vị trí cao; MRR đo vị trí kết quả đúng đầu tiên. Trên tập thử thách ngữ nghĩa, Vector không rerank tăng Hit@5 từ 0,756 lên 1,000 và NDCG@5 từ 0,689 lên 0,941 so với BM25. Hybrid fusion tăng Strict Hit@5 từ 0,580 lên 0,920 so với text-only. Bật rerank làm chỉ số này giảm còn 0,670, nên cấu hình cuối tắt rerank. Image Search ảnh ngoài đạt Exact Hit@5 0,970; RAG nâng grounding từ 0,824 lên 1,000.

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

## Slide 30 — Kết luận

**Thông điệp kết thúc:** AI hỗ trợ quyết định; dữ liệu nghiệp vụ giữ quyền kiểm soát.

> Đề tài đóng góp một hệ thống end-to-end, một kiến trúc có đường biên trách nhiệm rõ ràng và một quy trình đánh giá bằng baseline, ablation cùng kiểm thử hệ thống. Kết luận áp dụng cho snapshot và tải đã đo, chưa đồng nghĩa production-ready.

## Slide 31 — Q&A

> Nhóm xin cảm ơn hội đồng và sẵn sàng trả lời câu hỏi. Mở đúng phụ lục theo chủ đề được hỏi.

## Slide 32 — Tài liệu tham khảo

Không trình bày nếu không được hỏi. Dùng để truy vết các nguồn ngoài ở slide 3 và slide 7; nguồn số liệu nội bộ nằm trong báo cáo và thư mục đánh giá.

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
