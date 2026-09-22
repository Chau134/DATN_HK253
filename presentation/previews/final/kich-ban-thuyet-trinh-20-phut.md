# Kịch bản thuyết trình đồ án — khoảng 20 phút

**Đề tài:** Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision
**Phạm vi trình bày:** Slide 1–27. Slide 28 dùng cho Q&A, slide 29 là tài liệu tham khảo; A1–A9 chỉ mở khi hội đồng hỏi sâu.
**Tổng thời lượng mục tiêu:** khoảng 18–19 phút, còn khoảng đệm cho chuyển slide và tương tác với hội đồng.

## Phân bổ thời gian

| Phần | Slide | Thời lượng |
|---|---:|---:|
| Mở đầu và bài toán | 1–8 | 3 phút 30 giây |
| Phân tích và thiết kế | 9–16 | 4 phút 30 giây |
| Sản phẩm và demo | 17–21 | 6 phút |
| Kiểm thử và đánh giá | 22–25 | 2 phút 50 giây |
| Kết luận và hướng phát triển | 26–27 | 1 phút |
| Chuyển slide và khoảng dừng nhấn ý | Toàn bài | khoảng 50 giây |

---

## Slide 1 — Trang bìa (20 giây)

> Kính thưa Hội đồng, em là Huỳnh Thái Minh Châu. Em xin trình bày đề tài “Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision”, dưới sự hướng dẫn của ThS. Võ Thanh Hùng. Ban đầu đề tài được đăng ký dưới 3 sinh viên, tuy nhiên 2 bạn còn lại chưa hoàn thành yêu cầu anh văn nên đã tách riêng nên chỉ còn 1 mình e thực hiện và trình bày.

## Slide 2 — Nội dung trình bày (10 giây)

> Bài trình bày gồm năm phần: bài toán, phân tích và thiết kế, sản phẩm và demo, kiểm thử đánh giá, cuối cùng là kết luận và hướng phát triển.

## Slide 3 — Bối cảnh và lý do chọn đề tài (30 giây)

> Ngày nay, nhu cầu mua sắm trực tuyến đang dần lớn và người dùng tìm kiếm sản phẩm chuyển dần từ từ khóa sang đa phương thức. Thực tế, Google Lens xử lý gần 20 tỷ lượt tìm kiếm trực quan mỗi tháng, trong đó khoảng 20 phần trăm liên quan đến mua sắm. Về công nghệ, CLIP giúp liên kết hình ảnh với văn bản, còn RAG giúp câu trả lời bám vào dữ liệu truy xuất. Từ bối cảnh và xu hướng công nghệ đề này sẽ giúp xây dựng hệ thống thương mại điện tử hoàn chỉnh, giúp người dùng tìm kiếm tư vấn mua sắm nhanh hơn.

## Slide 4 — Bài toán thực tế (35 giây)

> Em xác định ba điểm gãy chính. Thứ nhất là khoảng cách ngữ nghĩa: từ khóa không diễn đạt hết ý định. Thứ hai là khoảng cách thị giác: người dùng có ảnh nhưng khó mô tả chính xác. Thứ ba là mất ngữ cảnh giữa các lượt hỏi. Kết quả là hệ thống có thể trả nhiều sản phẩm nhưng vẫn chưa giúp người dùng ra quyết định nhanh hơn.

## Slide 5 — Mục tiêu đề tài (30 giây)

> Từ đó, em đặt ra bốn mục tiêu: hỗ trợ tìm kiếm bằng văn bản, hình ảnh và kết hợp; tư vấn có căn cứ bằng RAG và bộ nhớ hội thoại; tích hợp AI vào hành trình thương mại điện tử; và đánh giá giải pháp bằng chỉ số chất lượng, độ trễ cùng kiểm thử hệ thống.

## Slide 6 — Phạm vi và người dùng (25 giây)

> Hệ thống phục vụ khách hàng và quản trị viên trong miền thời trang. Phạm vi gồm khám phá sản phẩm, giỏ hàng, đặt hàng, quản trị và đồng bộ dữ liệu AI. Thanh toán thật, vận chuyển thực tế và hạ tầng thương mại quy mô lớn không nằm trong phạm vi của nguyên mẫu.

## Slide 7 — Giải pháp liên quan (30 giây)

> Shopee và Tiki đã hỗ trợ tìm kiếm bằng từ khóa, bộ lọc hoặc hình ảnh, nhưng chưa thể hiện rõ khả năng duy trì yêu cầu qua hội thoại nhiều lượt. Google Lens cho phép kết hợp hình ảnh với văn bản, nhưng không gắn với quy trình của một sàn thương mại điện tử cụ thể. Vì vậy, đề tài kết hợp tìm kiếm văn bản, hình ảnh, kết hợp cả 2 và hội thoại nhiều lượt.

## Slide 8 — Điểm khác biệt (30 giây)

> Điểm khác biệt của đề tài nằm ở một vòng lặp mua sắm hoàn chỉnh gồm bốn bước: hiểu văn bản và hình ảnh, truy hồi vector có ràng buộc, tư vấn bằng RAG và bộ nhớ, sau đó dẫn tới hành động mua hàng và phản hồi. Mũi tên quay lại thể hiện rằng phản hồi tiếp tục trở thành tín hiệu cho lượt sau. Giá trị không nằm ở một mô hình riêng lẻ mà ở cách các thành phần phối hợp và được kiểm chứng như một hệ thống.

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

## Slide 21 — Video demo (khoảng 3 phút 50 giây)

Kịch bản quay chi tiết, câu thoại, dữ liệu mẫu và checklist được lưu tại
`presentation/previews/final/kich-ban-quay-video-demo-du-an.md`.

**Lời mở video:**

> Video demo sau minh họa một hành trình xuyên suốt: tìm kiếm bằng văn bản, tìm bằng ảnh, kết hợp ảnh với ràng buộc văn bản, hội thoại nhiều lượt, rồi thêm sản phẩm vào giỏ và đặt hàng COD.

**Nhịp demo tóm tắt:**

- 00:00–00:30: giới thiệu trang chủ, danh mục, chi tiết, wishlist, blog và trang thông tin.
- 00:30–01:40: Text Search, Image Search và Hybrid Search.
- 01:40–02:40: hội thoại nhiều lượt để chứng minh bộ nhớ và RAG.
- 02:40–03:31: xem chi tiết, thêm giỏ và đặt COD.
- 03:31–03:52: đối chiếu đơn vừa tạo trong backoffice và kết video.

**Chuyển phần:**

> Demo vừa rồi cho thấy hệ thống hoạt động ở góc nhìn người dùng. Tiếp theo, em trình bày cách hệ thống được kiểm chứng theo ba lớp và các bằng chứng định lượng tương ứng.

---

## Slide 22 — Phạm vi kiểm thử (40 giây)

> Hệ thống được kiểm thử theo ba lớp. Thứ nhất, chất lượng AI trả lời câu hỏi kết quả tìm kiếm và tư vấn có đúng, đồng thời có tốt hơn baseline hay không. Thứ hai, chức năng và tích hợp kiểm tra request có được xử lý đúng, dữ liệu MySQL–Qdrant có nhất quán, và các cơ chế end-to-end, retry, rollback, fallback có hoạt động hay không. Thứ ba, phi chức năng đánh giá độ ổn định, an toàn và tương thích. Cả ba lớp dùng chung snapshot cố định, fixture, seed, gate nghiệm thu và artifact có thể tái lập.

## Slide 23 — Quy trình kiểm thử (55 giây)

> Từ đầu vào chung đó, mỗi lớp có một quy trình kiểm chứng riêng. Với AI, em xây dựng ground truth, chạy baseline và ablation, đo metric rồi chọn cấu hình đạt gate. Với chức năng và tích hợp, em chuẩn bị test case và fixture, chạy API cùng các luồng end-to-end, đối chiếu dữ liệu, sau đó kiểm tra retry, rollback và fallback. Với phi chức năng, em xác định workload và rủi ro, chạy load, security và kiểm thử trình duyệt, rồi thu P95 cùng số lỗi để đánh giá giới hạn. Mỗi quy trình đều tạo evidence artifact và kết luận theo ba mức: đạt, đạt có giới hạn hoặc chưa đạt.

## Slide 24 — Kết quả kiểm thử chính (50 giây)

> Đây là ba bằng chứng chính. Về AI, Text Hit@5 đạt 1,000 so với 0,756 của BM25; Hybrid Strict Hit@5 đạt 0,980 và RAG Grounding đạt 1,000. Image Search trên ảnh bên ngoài đạt Exact Hit@5 là 0,970, nhưng được ghi nhận là đạt có giới hạn. Về chức năng và tích hợp, 102 trên 102 ca nghiệp vụ, năm trên năm luồng end-to-end và đồng bộ 1.000 trên 1.000 product ID đều đạt; retry, rollback và fallback cũng hoạt động đúng. Về phi chức năng, bài soak hai giờ hoàn tất 57.600 request với 0 lỗi, P95 Catalog–Cart là 182,79 mili giây, security gate và tám trên tám ca Firefox–WebKit đều đạt. Tuy nhiên, kết quả phi chức năng chỉ có giá trị trong môi trường thử, chưa thay thế pentest và kiểm tra trên thiết bị thật.

## Slide 25 — Tổng hợp kết quả (25 giây)

> Tổng hợp theo đúng phạm vi bằng chứng: Text Search, Hybrid Search, RAG và Memory, cùng nghiệp vụ và tích hợp đều đạt. Image Search đạt có giới hạn do chất lượng suy giảm trên ảnh bên ngoài; phi chức năng đạt trong phạm vi load, security, health và browser đã kiểm tra. Vì vậy, hệ thống đạt tiêu chí nghiệm thu nội bộ trong phạm vi đồ án, nhưng chưa thể xem là đã sẵn sàng vận hành thương mại quy mô lớn.

## Slide 26 — Kết luận (30 giây)

> Đề tài đã hoàn thành bốn nhóm mục tiêu. Thứ nhất là sản phẩm thương mại điện tử cho khách hàng và quản trị viên. Thứ hai là năng lực AI đa phương thức gồm Text, Image, Hybrid Search, YOLOv26, RAG và bộ nhớ hội thoại. Thứ ba là kiến trúc React, Spring Boot, FastAPI, MySQL và Qdrant, được đóng gói Docker và triển khai thử nghiệm trên Google Cloud. Cuối cùng, hệ thống đã được kiểm thử: AI đạt các gate, Backend đạt 102 trên 102 ca, năm luồng end-to-end đạt và đồng bộ đủ 1.000 product ID.

## Slide 27 — Hướng phát triển (30 giây)

> Hướng phát triển gồm sáu nhóm: mở rộng dữ liệu; cải thiện tìm kiếm; cá nhân hóa có quyền kiểm soát dữ liệu; hoàn thiện thanh toán, vận chuyển, đổi trả và ứng dụng di động; tăng khả năng phục vụ bằng autoscale, hàng đợi và bản sao dữ liệu; cuối cùng là pentest, diễn tập khôi phục, dashboard vận hành và đánh giá với người dùng thực. Thứ tự ưu tiên trước mắt là mở rộng dữ liệu đánh giá, cải thiện tìm kiếm kết hợp, sau đó mới tăng tải, bảo mật và khả năng quan sát.

## Slide 28 — Q&A

> Em xin cảm ơn Hội đồng đã lắng nghe và sẵn sàng trả lời câu hỏi. Khi trao đổi, ưu tiên mở đúng phụ lục theo nhóm câu hỏi: ma trận kiểm thử, hiệu năng, API, lỗi đã khắc phục, YOLO hoặc bản đồ bằng chứng.

## Slide 29 — Tài liệu tham khảo

Không trình bày thành lời nếu không được hỏi. Các mục [1]–[6] là nguồn ngoài cho slide 3 và slide 7; nguồn nội bộ trỏ tới báo cáo cùng các artifact đánh giá.

---

## Phụ lục — chỉ mở khi hội đồng hỏi

### A1 — Ma trận kiểm thử

Dùng khi hội đồng hỏi quy mô bộ đánh giá, số lượng ca hoặc tiêu chí nghiệm thu. Nhấn mạnh rằng mỗi nhóm chức năng có metric và gate riêng; không dùng một chỉ số duy nhất để kết luận toàn hệ thống.

### A2 — Hiệu năng chi tiết

Dùng khi hỏi về P50, P95, P99, throughput hoặc tác động tối ưu. Slide thể hiện tải Backend 6.050 request, soak hai giờ 57.600 request và tập tải AI tổng hợp 360 request; P95 Text, Hybrid và Assistant tương ứng là 1,412; 0,516 và 2,776 giây. Đây là các phạm vi đo khác nhau, vì vậy không so sánh trực tiếp độ trễ giữa các workload.

### A3 — Danh sách API

Dùng khi hỏi cách phân chia Spring Boot và FastAPI. Spring Boot công khai API nghiệp vụ; FastAPI chỉ phục vụ AI và vận hành nội bộ.

### A4 — Lỗi đã phát hiện và khắc phục

Dùng khi hỏi bài học kỹ thuật. Có thể chọn một ví dụ tiêu biểu: tắt rerank sau ablation vì làm giảm NDCG và Hit@5; hoặc tối ưu cache và chỉ mục để giảm P95 tải hỗn hợp từ 693,46 xuống 182,79 mili giây.

### A5 — Kết quả fine-tune YOLOv26s

> Mô hình YOLOv26s được fine-tune trên dữ liệu Fashionpedia đã gom thành bốn lớp: Clothing, Shoes, Bags và Accessories. Trên 2.339 ảnh với 8.226 đối tượng, mô hình đạt Precision 0,875, Recall 0,760, mAP50 0,849 và mAP50–95 0,685. mAP50 theo từng lớp lần lượt là 0,947; 0,945; 0,807 và 0,695. YOLO chỉ là bước crop tùy chọn: nếu không phát hiện hoặc độ tin cậy thấp, pipeline dùng ảnh gốc để tiếp tục tạo embedding.

### A6 — Bản đồ bằng chứng

Dùng khi hội đồng yêu cầu nguồn số liệu. Chỉ ra rằng báo cáo, file cấu hình, kết quả từng truy vấn và artifact hiệu năng đều được lưu trong repository để có thể kiểm tra lại.

### A7 — Thiết kế đánh giá AI và ngưỡng nghiệm thu

Dùng khi hội đồng hỏi quy mô ground truth, metric, gate hoặc cách thiết kế phép so sánh cho Text, Image, Hybrid Search và RAG. Nhấn mạnh rằng từng chức năng có tiêu chí riêng và P95 chỉ được so sánh trong cùng workload.

### A8 — Kết quả baseline và ablation chi tiết

Dùng khi hội đồng hỏi tại sao chọn Vector, Image-conditioned hoặc tắt rerank. Các chênh lệch được đo trên cùng tập dữ liệu; không kết luận rerank luôn kém, chỉ kết luận cấu hình rerank hiện tại không phù hợp với tập thử.

### A9 — Bằng chứng tích hợp và phi chức năng

Dùng khi hội đồng hỏi số lượng API, ca nghiệp vụ, tính nhất quán MySQL–Qdrant, URL ảnh, correlation ID, hiệu năng, soak, bảo mật hoặc trình duyệt. Các số liệu chi tiết được đưa xuống phụ lục để phần trình bày chính chỉ giữ kết luận và ba bằng chứng đại diện.

## Các nguyên tắc khi trình bày

- Không nói hệ thống đã sẵn sàng production.
- Không nói Image Search “chính xác 97%” chung chung; đây là **Exact Hit@5 trên tập challenging**.
- Không nói rerank luôn kém; chỉ kết luận rerank không phù hợp với cấu hình và tập thử hiện tại.
- Không gọi WebKit tự động là Safari trên thiết bị thật.
- Không đồng nhất “0 lỗi trong bài tải” với “hệ thống không có lỗi”.
- Khi gần hết giờ, rút ngắn slide 24 và 26; không bỏ quy trình ba lớp ở slide 23 hoặc giới hạn kết luận ở slide 25.
