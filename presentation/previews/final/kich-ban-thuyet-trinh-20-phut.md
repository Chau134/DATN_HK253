# Kịch bản thuyết trình đồ án — khoảng 20 phút

**Đề tài:** Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision
**Phạm vi trình bày:** Slide 1–30. Slide 31 dùng cho Q&A, slide 32 là tài liệu tham khảo; A1–A6 chỉ mở khi hội đồng hỏi sâu.
**Tổng thời lượng mục tiêu:** 19 phút 30 giây đến 20 phút.

## Phân bổ thời gian

| Phần | Slide | Thời lượng |
|---|---:|---:|
| Mở đầu và bài toán | 1–8 | 3 phút 30 giây |
| Phân tích và thiết kế | 9–16 | 4 phút 30 giây |
| Sản phẩm và demo | 17–21 | 4 phút 40 giây |
| Kiểm thử và đánh giá | 22–29 | 5 phút 30 giây |
| Kết luận | 30 | 30 giây |
| Chuyển slide và khoảng dừng nhấn ý | Toàn bài | khoảng 50 giây |

---

## Slide 1 — Trang bìa (20 giây)

> Kính thưa hội đồng, em xin trình bày đề tài “Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision”. Đề tài ban đầu được đăng ký với ba sinh viên; tuy nhiên, hai thành viên còn lại chưa kịp hoàn thành yêu cầu anh văn nên đã tách sang đồ án riêng, nên nội dung đồ án này do một mình em thực hiện và trình bày. Mục tiêu của đề tài là xây dựng một hệ thống thương mại điện tử hoàn chỉnh, trong đó người dùng có thể tìm kiếm và nhận tư vấn bằng văn bản, hình ảnh và hội thoại nhiều lượt.

## Slide 2 — Nội dung trình bày (10 giây)

> Bài trình bày gồm năm phần: bài toán, phân tích và thiết kế, sản phẩm và demo, kiểm thử đánh giá, cuối cùng là kết luận và hướng phát triển.

## Slide 3 — Bối cảnh và lý do chọn đề tài (30 giây)

> Hành vi tìm kiếm mua sắm đang chuyển từ từ khóa sang đa phương thức. Theo Google, Lens xử lý gần 20 tỷ lượt tìm kiếm trực quan mỗi tháng và khoảng 20 phần trăm liên quan đến mua sắm. Về nền tảng kỹ thuật, RAG nối mô hình sinh với dữ liệu truy xuất, còn CLIP cho thấy khả năng học biểu diễn ảnh–văn bản từ 400 triệu cặp. Vì vậy, bài toán thực tế là kết nối mô tả, ảnh tham chiếu và ngữ cảnh hội thoại với dữ liệu sản phẩm có thể kiểm chứng.

## Slide 4 — Bài toán thực tế (35 giây)

> Em xác định ba điểm gãy chính. Thứ nhất là khoảng cách ngữ nghĩa: từ khóa không diễn đạt hết ý định. Thứ hai là khoảng cách thị giác: người dùng có ảnh nhưng khó mô tả chính xác. Thứ ba là mất ngữ cảnh giữa các lượt hỏi. Kết quả là hệ thống có thể trả nhiều sản phẩm nhưng vẫn chưa giúp người dùng ra quyết định nhanh hơn.

## Slide 5 — Mục tiêu đề tài (30 giây)

> Từ đó, em đặt ra bốn mục tiêu: hỗ trợ tìm kiếm bằng văn bản, hình ảnh và kết hợp; tư vấn có căn cứ bằng RAG và bộ nhớ hội thoại; tích hợp AI vào hành trình thương mại điện tử; và đánh giá giải pháp bằng chỉ số chất lượng, độ trễ cùng kiểm thử hệ thống.

## Slide 6 — Phạm vi và người dùng (25 giây)

> Hệ thống phục vụ khách hàng và quản trị viên trong miền thời trang. Phạm vi gồm khám phá sản phẩm, giỏ hàng, đặt hàng, quản trị và đồng bộ dữ liệu AI. Thanh toán thật, vận chuyển thực tế và hạ tầng thương mại quy mô lớn không nằm trong phạm vi của nguyên mẫu.

## Slide 7 — Giải pháp liên quan (30 giây)

> Google Lens mạnh ở đầu vào hình ảnh và quy mô tìm kiếm trực quan, nhưng không quản lý source of truth hay giao dịch của từng cửa hàng. Google AI Commerce Search khai thác catalog và sự kiện người dùng để tìm kiếm, gợi ý, nhưng vẫn là dịch vụ managed cần tích hợp với nghiệp vụ. Alexa for Shopping, trước đây là Rufus, mạnh ở hội thoại mua sắm dựa trên catalog, review và thông tin web, nhưng vận hành trong hệ sinh thái đóng. Giải pháp đề xuất kết nối Text, Image, Hybrid Search, RAG và memory với Backend xác nhận giá, tồn kho và giao dịch; đổi lại, bằng chứng hiện mới ở quy mô nguyên mẫu 1.000 sản phẩm.

## Slide 8 — Điểm khác biệt (30 giây)

> Điểm khác biệt không chỉ là gọi một mô hình AI. Giải pháp tạo một vòng lặp end-to-end: hiểu yêu cầu, truy hồi có ràng buộc, tư vấn dựa trên dữ liệu, rồi đưa người dùng trở lại hành động mua hàng.

**Chuyển phần:**

> Sau khi xác định bài toán, em xin trình bày cách phân tích và thiết kế hệ thống.

---

## Slide 9 — Yêu cầu chức năng (30 giây)

> Em xây dựng 17 yêu cầu chức năng. Năm yêu cầu thương mại điện tử tạo hành trình từ tài khoản đến đặt và theo dõi đơn. Mười hai yêu cầu AI bao phủ tìm kiếm, hiểu truy vấn, hội thoại, xếp hạng, vận hành và dự phòng. Nguyên tắc ưu tiên là tìm đúng, trả lời có căn cứ và không làm gián đoạn nghiệp vụ.

## Slide 10 — Yêu cầu phi chức năng (30 giây)

> Ngoài chức năng, hệ thống cần có độ trễ phù hợp, dữ liệu nhất quán, bảo mật, khả dụng và khả năng quan sát. Với quy mô thử nghiệm từ 500 đến 2.000 sản phẩm, em đặt ngưỡng riêng cho nghiệp vụ lõi và tác vụ AI để kết quả có thể đo và nghiệm thu.

## Slide 11 — Use case tổng quan (25 giây)

> Ba tác nhân có trách nhiệm rõ ràng. Khách hàng mua sắm và dùng trợ lý; quản trị viên vận hành dữ liệu và đơn hàng; AI Service cung cấp tìm kiếm, hội thoại và quản lý chỉ mục. Kết quả cuối cùng vẫn đi qua Backend để kiểm tra dữ liệu hiện hành.

## Slide 12 — Kiến trúc tổng thể (45 giây)

> Frontend chỉ giao tiếp với Spring Boot. Backend đảm nhiệm xác thực, phân quyền, transaction và là cổng công khai duy nhất. FastAPI xử lý workflow AI; MySQL giữ dữ liệu nghiệp vụ; Qdrant giữ vector phục vụ truy hồi; Redis hoặc checkpoint lưu trạng thái cần thiết. AI chỉ đề xuất định danh sản phẩm, còn giá, tồn kho và trạng thái bán luôn được Backend xác nhận từ MySQL.

## Slide 13 — Luồng hoạt động chính (40 giây)

> Đầu vào có thể là văn bản, ảnh hoặc cả hai. Hệ thống phân tích ý định và ràng buộc, tạo embedding, truy hồi Qdrant rồi hợp nhất ứng viên. Sau đó Backend lấy dữ liệu nghiệp vụ mới nhất trước khi trả kết quả. Bộ nhớ lưu các ràng buộc cho câu hỏi tiếp theo; nếu một nhánh AI lỗi, hệ thống vẫn có cơ chế suy giảm phù hợp.

## Slide 14 — Thiết kế cơ sở dữ liệu (30 giây)

> MySQL là nguồn dữ liệu chuẩn cho giao dịch, giá và tồn kho. Qdrant chỉ lưu chỉ mục vector dẫn xuất; Redis lưu cache hoặc trạng thái ngắn hạn. Việc tách quyền sở hữu dữ liệu giúp các kho phục vụ AI có thể tái tạo mà không ảnh hưởng tính đúng đắn của đơn hàng.

## Slide 15 — Công nghệ sử dụng (30 giây)

> React được dùng cho giao diện SPA; Spring Boot cho nghiệp vụ và transaction; FastAPI cùng LangGraph cho workflow AI có trạng thái. MySQL, Qdrant và Redis đảm nhiệm các loại dữ liệu khác nhau. Ngoài ra, mô hình và hạ tầng có sử dụng: Bedrock, cohere embedv4, yolo, docker và GCP.

## Slide 16 — Quyết định kỹ thuật quan trọng (40 giây)

> Bốn quyết định chính là: Spring Boot làm cổng công khai duy nhất; MySQL giữ quyền quyết định dữ liệu nghiệp vụ; AI Service được tách và có fallback; các provider được cấu hình qua adapter, khi sửa provider không cần sửa toàn bộ hệ thống. Nhờ đó, AI hỗ trợ quá trình ra quyết định nhưng không có quyền tự thay đổi giá, tồn kho hoặc trạng thái giao dịch.

**Chuyển phần:**

> Từ thiết kế trên, em đã hiện thực sản phẩm gồm cửa hàng, trợ lý AI và khu vực quản trị.

---

## Slide 17 — Tổng quan sản phẩm (30 giây)

> Sản phẩm hoàn thiện gồm ba không gian. Cửa hàng trực tuyến phục vụ hành trình mua sắm; trợ lý AI cung cấp tìm kiếm và tư vấn đa phương thức; backoffice hỗ trợ quản trị danh mục, đơn hàng và đồng bộ chỉ mục. Ba khu vực sử dụng chung dữ liệu và quy tắc nghiệp vụ.

## Slide 18 — Tìm kiếm đa phương thức (35 giây)

> Text Search phù hợp với mô tả tự nhiên và điều kiện về giá hoặc thuộc tính. Image Search tìm sản phẩm gần nhau về thị giác. Hybrid Search dùng ảnh để giữ kiểu dáng và dùng văn bản để bổ sung ràng buộc như màu, chất liệu hoặc ngân sách. Đây là chức năng trung tâm của đề tài.

## Slide 19 — RAG và bộ nhớ hội thoại (35 giây)

> Trợ lý không xử lý mỗi câu hỏi độc lập. Bộ nhớ khôi phục lựa chọn và ràng buộc ở lượt trước. Khi câu hỏi cần dữ kiện, hệ thống truy hồi sản phẩm và đưa context vào bước sinh phản hồi. Vì vậy, câu hỏi như “mẫu thứ hai còn màu đen không?” vẫn có thể được hiểu đúng và trả lời dựa trên dữ liệu.

## Slide 20 — Tích hợp hành trình mua hàng (30 giây)

> Kết quả AI được nối trực tiếp với trang chi tiết, giỏ hàng và đặt COD. Trước khi tạo đơn, Backend kiểm tra biến thể, tồn kho, địa chỉ và coupon trong transaction. Nhờ vậy, trải nghiệm tìm kiếm và tư vấn không bị tách khỏi nghiệp vụ thương mại điện tử.

## Slide 21 — Video demo (2 phút 30 giây)

**Lời mở video:**

> Video sau minh họa một hành trình xuyên suốt: tìm kiếm bằng văn bản, tìm bằng ảnh, kết hợp ảnh với ràng buộc văn bản, hội thoại nhiều lượt, rồi thêm sản phẩm vào giỏ và đặt hàng.

**Nhịp demo đề xuất:**

- 00:00–00:25: giới thiệu trang chủ và Text Search.
- 00:25–00:50: Image Search bằng ảnh tham chiếu.
- 00:50–01:15: Hybrid Search với màu hoặc ngân sách.
- 01:15–01:45: hỏi tiếp trong hội thoại để chứng minh bộ nhớ.
- 01:45–02:15: xem chi tiết, thêm giỏ và đặt COD.
- 02:15–02:30: cho thấy backoffice hoặc quá trình đồng bộ chỉ mục.

**Chuyển phần:**

> Demo cho thấy hệ thống hoạt động ở góc nhìn người dùng. Tiếp theo, em trình bày các bằng chứng định lượng để đánh giá chất lượng và tính đúng đắn.

---

## Slide 22 — Chiến lược và môi trường kiểm thử (45 giây)

> Em chia đánh giá thành hai lớp độc lập. Lớp thứ nhất đo chất lượng AI trên 100 truy vấn Text Search, 100 cặp ảnh, 100 truy vấn Hybrid, 80 câu hỏi RAG và 230 request phiên dài. Lớp thứ hai kiểm tra hệ thống hoàn chỉnh, gồm Backend, hợp đồng dịch vụ, đồng bộ dữ liệu, end-to-end và các thuộc tính phi chức năng. Mọi lần chạy sử dụng snapshot 1.000 sản phẩm, schema MySQL test, Qdrant collection riêng, cùng manifest, seed và ground truth đóng băng. Về nhãn đánh giá, Text Search có 2.703 nhãn được đối chiếu trên toàn snapshot; Image Search có 2.935 nhãn từ pooling Top-20, duyệt thị giác và luật metadata; Hybrid có 654 nhãn với toàn bộ candidate được duyệt thủ công; còn RAG dùng 80 bộ question, reference và evidence được duyệt theo ba lớp.

## Slide 23 — Tiêu chí đánh giá AI Service (45 giây)

> Mỗi chức năng cần một bộ chỉ số riêng. Hit@5 trả lời có ít nhất một kết quả đúng trong năm vị trí đầu hay không; NDCG ưu tiên kết quả liên quan cao xuất hiện sớm; MRR đo vị trí của kết quả đúng đầu tiên. Với ảnh, Exact Hit kiểm tra đúng sản phẩm nguồn, còn NDCG và mAP đo xếp hạng các sản phẩm tương tự. Với Hybrid, Strict Hit yêu cầu có ứng viên thỏa toàn bộ ý định và tỷ lệ thỏa ràng buộc đo từng kết quả Top-5. Với RAG, grounding đo phát biểu có bằng chứng, còn Context Precision và Recall đo mức ít nhiễu và không bỏ sót. P95 được tính trên biên client end-to-end và không so trực tiếp giữa các workload khác nhau.

## Slide 24 — Thiết kế so sánh (45 giây)

> Để so sánh công bằng, mỗi thí nghiệm giữ nguyên dữ liệu và chỉ thay thành phần cần kiểm chứng. Text Search so BM25 với Vector trước và sau rerank. Image Search ghép cặp cùng 100 sản phẩm giữa ảnh catalog và ảnh bên ngoài. Hybrid Search so năm cấu hình từ image-only, text-only, post-filter đến fusion có hoặc không rerank. Trợ lý được ablation từ LLM thuần, thêm RAG, thêm memory rồi thêm rerank. Cấu hình cuối được chọn theo chất lượng, gate và độ trễ, không mặc định giải pháp phức tạp hơn sẽ tốt hơn.

## Slide 25 — Kết quả so sánh baseline (55 giây)

> Trên cùng tập thử thách ngữ nghĩa, Vector không rerank tăng Hit@5 từ 0,756 của BM25 lên 1,000, tức tăng 0,244; NDCG@5 tăng từ 0,689 lên 0,941, tức tăng 0,252. Với Hybrid, fusion không rerank tăng Strict Hit@5 từ 0,580 của text-only lên 0,920, tăng 0,340. Tuy nhiên, khi bật rerank, chỉ số này giảm từ 0,920 xuống 0,670; vì vậy em tắt rerank theo bằng chứng thay vì mặc định cấu hình phức tạp hơn sẽ tốt hơn. Ở hai nhóm còn lại, Image Search trên ảnh ngoài đạt Exact Hit@5 0,970; RAG nâng grounding từ 0,824 lên 1,000 và critical gate từ 4 trên 12 lên 12 trên 12.

## Slide 26 — API và tích hợp (30 giây)

> Hệ thống có 26 Spring Controller với 126 request mapping và 14 endpoint FastAPI. Em kiểm tra hợp đồng request–response, API key nội bộ, full và incremental sync, retry, snapshot, rollback và fallback khi AI lỗi. Hai collection có đủ 1.000 product ID; correlation ID được truyền xuyên từ Backend sang AI Service để truy vết request.
**giải thích: “Ở phần tích hợp, em kiểm tra dữ liệu trao đổi giữa các dịch vụ có đúng định dạng hay không; các API nội bộ có được bảo vệ hay không; dữ liệu từ MySQL sang Qdrant có được đồng bộ đầy đủ và chính xác hay không. Em cũng kiểm tra khả năng thử lại khi xảy ra lỗi, lưu trạng thái cũ để phục hồi, quay lại phiên bản ổn định khi cập nhật thất bại và duy trì các chức năng cốt lõi khi AI Service không hoạt động.”
## Slide 27 — Phi chức năng (50 giây)

> Tải Backend hoàn tất 21.231 trên 21.231 request. P95 tải hỗn hợp Catalog–Cart sau tối ưu là 182,79 mili giây. Bài soak checkout và payment chạy tám worker trong hai giờ, đạt 57.600 trên 57.600 request, P95 48,863 mili giây và không lỗi. Tải AI đại diện đạt 216 trên 216 request; P95 của Text Search, Hybrid Search và Assistant lần lượt là 1,412; 3,412 và 2,776 giây. Các kiểm thử JWT, RBAC, IDOR, injection, rate limit và upload đều đạt; Playwright đạt 8 trên 8 ca Firefox và WebKit. Giới hạn còn lại là chưa có pentest độc lập và chưa xác nhận Safari trên thiết bị thật.

## Slide 28 — Tổng hợp kết quả (35 giây)

> Text Search, RAG, nghiệp vụ và tích hợp đạt các gate đặt ra. Image Search đạt có giới hạn vì suy giảm trên ảnh bên ngoài và ground truth similarity còn dùng một phần nhãn theo luật. Hybrid Search đạt một phần vì tỷ lệ Top-5 thỏa đồng thời mọi ràng buộc chỉ đạt 0,450. Nhìn chung, hệ thống đạt tiêu chí nghiệm thu nội bộ trong phạm vi đồ án, nhưng kết quả này chưa phải chứng nhận production-ready.

## Slide 29 — Hạn chế và hướng phát triển (35 giây)

> Các hạn chế chính là benchmark 1.000 sản phẩm chưa hoàn toàn held-out; Hybrid Search chưa giữ tốt đồng thời mọi ràng buộc; BM25 chưa đo latency và hai lượt P95 rerank chưa phải phép đo paired; tải AI mới chạy sáu worker trong ba phút, trong khi P99 Assistant còn 9,704 giây. Thứ tự ưu tiên là hoàn thiện constraint của Hybrid Search, xây dựng benchmark held-out, chạy tải AI dài và paired đầy đủ, rồi thực hiện pentest và đánh giá trên thiết bị thật.

## Slide 30 — Kết luận (30 giây)

> Đề tài đóng góp một hệ thống end-to-end tích hợp tìm kiếm đa phương thức, RAG và hành trình mua sắm; một kiến trúc có đường biên trách nhiệm rõ ràng; cùng quy trình đánh giá dựa trên baseline, ablation và kiểm thử hệ thống. Thông điệp em muốn nhấn mạnh là: AI hỗ trợ quyết định, còn dữ liệu nghiệp vụ luôn giữ quyền kiểm soát. Kết luận này áp dụng cho snapshot 1.000 sản phẩm và các tải đã đo, chưa đồng nghĩa production-ready.

## Slide 31 — Q&A

> Em xin cảm ơn Hội đồng đã lắng nghe và sẵn sàng trả lời câu hỏi. Khi trao đổi, ưu tiên mở đúng phụ lục theo nhóm câu hỏi: ma trận kiểm thử, hiệu năng, ERD, API, lỗi đã khắc phục hoặc bản đồ bằng chứng.

## Slide 32 — Tài liệu tham khảo

Không trình bày thành lời nếu không được hỏi. Các mục [1]–[5] là nguồn ngoài cho slide 3 và slide 7; nguồn nội bộ trỏ tới báo cáo cùng các artifact đánh giá.

---

## Phụ lục — chỉ mở khi hội đồng hỏi

### A1 — Ma trận kiểm thử

Dùng khi hội đồng hỏi quy mô bộ đánh giá, số lượng ca hoặc tiêu chí nghiệm thu. Nhấn mạnh rằng mỗi nhóm chức năng có metric và gate riêng; không dùng một chỉ số duy nhất để kết luận toàn hệ thống.

### A2 — Hiệu năng chi tiết

Dùng khi hỏi về P50, P95, P99, throughput hoặc tác động tối ưu. Nêu rõ ba phạm vi khác nhau: tải Backend, soak checkout/payment hai giờ và tải AI đồng thời. Không so sánh trực tiếp độ trễ giữa các workload khác nhau.

### A3 — ERD tổng thể

Dùng khi hỏi quan hệ dữ liệu, khóa ngoại hoặc quyền sở hữu dữ liệu. Câu trả lời cốt lõi: MySQL là nguồn chuẩn cho nghiệp vụ; vector và cache là dữ liệu dẫn xuất.

### A4 — Danh sách API

Dùng khi hỏi cách phân chia Spring Boot và FastAPI. Spring Boot công khai API nghiệp vụ; FastAPI chỉ phục vụ AI và vận hành nội bộ.

### A5 — Lỗi đã phát hiện và khắc phục

Dùng khi hỏi bài học kỹ thuật. Có thể chọn một ví dụ tiêu biểu: tắt rerank sau ablation vì làm giảm NDCG và Hit@5; hoặc tối ưu cache và chỉ mục để giảm P95 tải hỗn hợp từ 693,46 xuống 182,79 mili giây.

### A6 — Bản đồ bằng chứng

Dùng khi hội đồng yêu cầu nguồn số liệu. Chỉ ra rằng báo cáo, file cấu hình, kết quả từng truy vấn và artifact hiệu năng đều được lưu trong repository để có thể kiểm tra lại.

## Các nguyên tắc khi trình bày

- Không nói hệ thống đã sẵn sàng production.
- Không nói Image Search “chính xác 97%” chung chung; đây là **Exact Hit@5 trên tập challenging**.
- Không nói rerank luôn kém; chỉ kết luận rerank không phù hợp với cấu hình và tập thử hiện tại.
- Không gọi WebKit tự động là Safari trên thiết bị thật.
- Không đồng nhất “0 lỗi trong bài tải” với “hệ thống không có lỗi”.
- Khi gần hết giờ, rút ngắn slide 26 và 29; không cắt cách đánh giá ở slide 23–24 hoặc kết quả chính ở slide 25 và 27.
