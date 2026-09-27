# Kịch bản thuyết trình đồ án — khoảng 20 phút

**Đề tài:** Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision
**Phạm vi trình bày:** Slide 1–27. Slide 28 dùng cho Q&A, slide 29 là tài liệu tham khảo; A1–A9 chỉ mở khi hội đồng hỏi sâu.
**Tổng thời lượng mục tiêu:** khoảng 18 phút 35 giây, còn hơn 1 phút đệm trong khung 20 phút để chuyển slide và tương tác với hội đồng.

## Phân bổ thời gian

| Phần | Slide | Thời lượng |
|---|---:|---:|
| Mở đầu và bài toán | 1–8 | 3 phút 50 giây |
| Phân tích và thiết kế | 9–16 | 4 phút 30 giây |
| Sản phẩm và chức năng | 17–20 | 2 phút 10 giây |
| Kiểm thử và đánh giá | 21–24 | 2 phút 50 giây |
| Kết luận và hướng phát triển | 25–26 | 1 phút 15 giây |
| Video demo | 27 | 3 phút 50 giây |
| Chuyển slide và khoảng dừng nhấn ý | Toàn bài | khoảng 50 giây |

---

## Slide 1 — Trang bìa (20 giây)

> Kính thưa Hội đồng, em là Huỳnh Thái Minh Châu. Em xin trình bày đề tài “Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision”, dưới sự hướng dẫn của ThS. Võ Thanh Hùng. Ban đầu đề tài được đăng ký với ba sinh viên; tuy nhiên, hai bạn còn lại chưa hoàn thành yêu cầu ngoại ngữ nên đã tách riêng. Vì vậy, phần đồ án này do một mình em thực hiện và trình bày.

## Slide 2 — Lộ trình trình bày (15 giây)

> Bài trình bày gồm năm phần: mở đầu và bài toán; phân tích và thiết kế; sản phẩm và các chức năng nổi bật; kiểm thử và đánh giá; cuối cùng là kết luận, hướng phát triển, video demo và trao đổi.

## Slide 3 — Bối cảnh và lý do lựa chọn đề tài (40 giây)

> Như mọi người đã biết mua sắm online đang ngày càng phổ biến và hành vi tìm kiếm sản phẩm đang chuyển từ từ khóa sang đa phương thức. Theo dữ liệu Google Lens xử lý gần 20 tỷ lượt tìm kiếm trực quan mỗi tháng, trong đó khoảng 20 phần trăm liên quan đến mua sắm. Đồng thời, xu hướng công nghệ rất phát triển,vì vậy, em lựa chọn xây dựng web tmđt kết hợp chức năng AI giúp người dùng tìm kiếm, tư vấn mua sắm nhanh hơn.

## Slide 4 — Bài toán thực tế (35 giây)

> Em xác định ba điểm gãy chính. Thứ nhất là khoảng cách ngữ nghĩa: từ khóa không diễn đạt hết ý định. Thứ hai là khoảng cách thị giác: người dùng có ảnh nhưng khó mô tả chính xác. Thứ ba là mất ngữ cảnh giữa các lượt hỏi. Kết quả là hệ thống có thể trả nhiều sản phẩm nhưng vẫn chưa giúp người dùng ra quyết định nhanh hơn.

## Slide 5 — Khảo sát giải pháp liên quan (35 giây)

> Shopee và Tiki đã hỗ trợ tìm kiếm bằng từ khóa, bộ lọc hoặc hình ảnh, nhưng các nguồn công khai chưa mô tả rõ khả năng duy trì ràng buộc qua hội thoại nhiều lượt. Google Lens cho phép kết hợp hình ảnh với văn bản, nhưng không gắn với quy trình tư vấn và giao dịch của một sàn cụ thể. Giải pháp đề xuất kết hợp Text, Image và Hybrid Search với RAG, bộ nhớ hội thoại và Backend xác nhận dữ liệu hiện hành. Giới hạn của đề tài là nguyên mẫu thời trang ở quy mô khoảng 1.000 sản phẩm.


## Slide 6 — Mục tiêu đề tài (30 giây)

> Từ bài toán trên, em đặt ra bốn mục tiêu: hỗ trợ tìm kiếm bằng văn bản, hình ảnh và truy vấn kết hợp; tư vấn có căn cứ bằng RAG và bộ nhớ hội thoại; tích hợp end-to-end giữa Frontend, Backend, AI Service, MySQL và Qdrant; cuối cùng là đánh giá giải pháp bằng chất lượng truy hồi, độ trễ, chức năng và bảo mật.

## Slide 7 — Phạm vi và người dùng (25 giây)

> Hệ thống phục vụ khách hàng và quản trị viên trong miền thời trang. Phạm vi gồm tìm kiếm đa phương thức, tư vấn RAG nhiều lượt, đồng bộ MySQL–Qdrant, website mua sắm, khu vực quản trị cùng kiểm thử chức năng và phi chức năng. Thanh toán trực tuyến thực tế, vận chuyển, chuỗi cung ứng, kho quy mô lớn và triển khai thương mại phân tán không nằm trong phạm vi của nguyên mẫu.

**Chuyển phần:**

> Sau khi xác định bài toán, em xin trình bày cách phân tích và thiết kế hệ thống.

---

## Slide 8 — Yêu cầu chức năng (30 giây)

> Em xây dựng 17 yêu cầu chức năng. Năm yêu cầu thương mại điện tử tạo hành trình từ tài khoản đến đặt và theo dõi đơn. Mười hai yêu cầu AI bao phủ tìm kiếm, hiểu truy vấn, hội thoại, xếp hạng, vận hành và dự phòng. Nguyên tắc ưu tiên là tìm đúng, trả lời có căn cứ và không làm gián đoạn nghiệp vụ.

## Slide 9 — Yêu cầu phi chức năng (30 giây)

> Ngoài chức năng, hệ thống cần có độ trễ phù hợp, dữ liệu nhất quán, bảo mật, khả dụng và khả năng quan sát. Với quy mô thử nghiệm từ 500 đến 2.000 sản phẩm, em đặt ngưỡng riêng cho nghiệp vụ lõi và tác vụ AI để kết quả có thể đo và nghiệm thu.

## Slide 10 — Use case tổng quan (25 giây)

> Ba tác nhân có trách nhiệm rõ ràng. Khách hàng mua sắm và dùng trợ lý; quản trị viên vận hành dữ liệu và đơn hàng; AI Service cung cấp tìm kiếm, hội thoại và quản lý chỉ mục. Kết quả cuối cùng vẫn đi qua Backend để kiểm tra dữ liệu hiện hành.

## Slide 11 — Kiến trúc tổng thể (45 giây)

> Frontend chỉ giao tiếp với Spring Boot. Backend đảm nhiệm xác thực, phân quyền, transaction và là cổng công khai duy nhất. FastAPI xử lý workflow AI; MySQL giữ dữ liệu nghiệp vụ; Qdrant giữ vector phục vụ truy hồi; Redis hoặc checkpoint lưu trạng thái cần thiết. AI chỉ đề xuất định danh sản phẩm, còn giá, tồn kho và trạng thái bán luôn được Backend xác nhận từ MySQL.

## Slide 12 — Luồng hoạt động chính (40 giây)

> Đầu vào có thể là văn bản, ảnh hoặc cả hai. Hệ thống phân tích ý định và ràng buộc, tạo embedding, truy hồi Qdrant rồi hợp nhất ứng viên. Sau đó Backend lấy dữ liệu nghiệp vụ mới nhất trước khi trả kết quả. Bộ nhớ lưu các ràng buộc cho câu hỏi tiếp theo; nếu một nhánh AI lỗi, hệ thống vẫn có cơ chế suy giảm phù hợp.

## Slide 13 — Thiết kế cơ sở dữ liệu (30 giây)

> MySQL là nguồn dữ liệu chuẩn cho giao dịch, giá và tồn kho. Qdrant chỉ lưu chỉ mục vector dẫn xuất; Redis lưu cache hoặc trạng thái ngắn hạn. Việc tách quyền sở hữu dữ liệu giúp các kho phục vụ AI có thể tái tạo mà không ảnh hưởng tính đúng đắn của đơn hàng.

## Slide 14 — Công nghệ sử dụng (30 giây)

> React được dùng cho giao diện SPA; Spring Boot cho nghiệp vụ và transaction; FastAPI cùng LangGraph cho workflow AI có trạng thái. MySQL, Qdrant và Redis đảm nhiệm các loại dữ liệu khác nhau. Ngoài ra, mô hình và hạ tầng có sử dụng: Bedrock, cohere embedv4, yolo, docker và GCP.

**Chuyển phần:**

> Từ thiết kế trên, em đã hiện thực sản phẩm gồm cửa hàng, trợ lý AI và khu vực quản trị.

---

## Slide 15 — Tổng quan sản phẩm (30 giây)

> Sản phẩm hoàn thiện gồm ba không gian. Cửa hàng trực tuyến phục vụ hành trình mua sắm; trợ lý AI cung cấp tìm kiếm và tư vấn đa phương thức; backoffice hỗ trợ quản trị danh mục, đơn hàng và đồng bộ chỉ mục. Ba khu vực sử dụng chung dữ liệu và quy tắc nghiệp vụ.

## Slide 18 — Tìm kiếm đa phương thức (35 giây)

>Đây là giao diện của trang tư vấn: hỗ trợ tìm kiếm đa phương thức. Hộp thoại thứ nhất cho phép tìm kiếm bằng văn bản, thứ hai hỗ trợ hình ảnh và thứ ba sẽ kết hợp cả hai. Ngoài ra, khi ở các trang khác, người dùng vẫn có thể sử dụng thanh tìm kiếm trên đầu trang để thực hiện các chức năng tương tự.

## Slide 19 — RAG và bộ nhớ hội thoại (35 giây)

> Trợ lý không xử lý mỗi câu hỏi độc lập. Bộ nhớ khôi phục lựa chọn và ràng buộc ở lượt trước. Khi câu hỏi cần dữ kiện, hệ thống truy hồi sản phẩm và đưa context vào bước sinh phản hồi. Vì vậy, câu hỏi như “mẫu thứ hai còn màu đen không?” vẫn có thể được hiểu đúng và trả lời dựa trên dữ liệu.

## Slide 20 — Tích hợp hành trình mua hàng (30 giây)

> Kết quả AI được nối trực tiếp với trang chi tiết, giỏ hàng và đặt COD. Trước khi tạo đơn, Backend kiểm tra biến thể, tồn kho, địa chỉ và coupon trong transaction. Nhờ vậy, trải nghiệm tìm kiếm và tư vấn không bị tách khỏi nghiệp vụ thương mại điện tử.

**Chuyển phần:**

> Các slide vừa rồi cho thấy hệ thống hoạt động ở góc nhìn sản phẩm. Tiếp theo, em trình bày cách hệ thống được kiểm chứng theo ba lớp và các bằng chứng định lượng tương ứng.

## Slide 21 — Phạm vi kiểm thử (40 giây)

> Hệ thống được kiểm thử theo ba lớp. Thứ nhất, chất lượng AI gồm tìm kiểm văn bản, hình ảnh, kết hợp cả hai và hội thoại nhiều lượt. Thứ hai, chức năng và tích hợp kiểm tra Backend, nghiệp vụ, đồng bộ MySQL–Qdrant và các luồng end-to-end. Thứ ba, phi chức năng đánh giá hiệu năng, bảo mật, khả dụng, khả năng quan sát và tương thích. Cả ba lớp dùng chung snapshot 1.000 sản phẩm, fixture, seed và ground truth được đóng băng.

## Slide 22 — Quy trình kiểm thử (55 giây)

> Từ đầu vào chung đó, mỗi lớp có một quy trình kiểm chứng riêng. Với AI, em xây dựng ground truth, chạy baseline và ablation, đo metric rồi chọn cấu hình đạt gate. Với chức năng và tích hợp, em chuẩn bị test case và fixture, chạy API cùng các luồng end-to-end, đối chiếu dữ liệu, sau đó kiểm tra retry, rollback và fallback. Với phi chức năng, em xác định workload và rủi ro, chạy load, security và kiểm thử trình duyệt, rồi thu P95 cùng số lỗi để đánh giá giới hạn. Mỗi quy trình đều tạo evidence artifact và kết luận theo ba mức: đạt, đạt có giới hạn hoặc chưa đạt.

## Slide 23 — Kết quả kiểm thử chính (50 giây)

> Đây là ba bằng chứng chính. Về AI, Text Image, Hybrid có Hit@5 cao hơn Hit của metrics baseline khác. RAG Grounding: kiểm tra câu hỏi có bẳng chứng đạt 1,000. Về chức năng và tích hợp, 102 trên 102 ca nghiệp vụ, năm trên năm luồng end-to-end và đồng bộ 1.000 trên 1.000 product ID đều đạt. Về phi chức năng, bài soak hai giờ hoàn tất 57.600 request với 0 lỗi, P95 Catalog–Cart là 182,79 mili giây
## Slide 24 — Tổng hợp kết quả (25 giây)

> Tổng hợp theo đúng phạm vi bằng chứng: Text Search, Hybrid Search, RAG và Memory, cùng nghiệp vụ và tích hợp đều đạt. Image Search đạt có giới hạn do chất lượng suy giảm trên ảnh bên ngoài; phi chức năng đạt trong phạm vi load, security, health và browser đã kiểm tra. Vì vậy, hệ thống đạt tiêu chí nghiệm thu nội bộ trong phạm vi đồ án, nhưng chưa thể xem là đã sẵn sàng vận hành thương mại quy mô lớn.

**Chuyển phần:**

> Từ các bằng chứng trên, em xin tổng kết kết quả, nêu rõ hạn chế và các hướng phát triển ưu tiên.

---

## Slide 25 — Kết luận (30 giây)

> Đề tài đã hoàn thành bốn nhóm mục tiêu. Thứ nhất là sản phẩm thương mại điện tử cho khách hàng và quản trị viên. Thứ hai là năng lực AI đa phương thức gồm Text, Image, Hybrid Search sử dụng YOLOv26, RAG và bộ nhớ hội thoại. Thứ ba là kiến trúc React, Spring Boot, FastAPI, MySQL và Qdrant, được đóng gói Docker và triển khai thử nghiệm trên Google Cloud. Cuối cùng, hệ thống đã được kiểm thử: AI đạt các gate, Backend, luồng end-to-end và đồng bộ dữ liệu đều đạt

## Slide 26 — Hạn chế và hướng phát triển (45 giây)

> Kết quả của đề tài cần được nhìn trong phạm vi kiểm chứng hiện tại. Thứ nhất, dữ liệu và ground truth còn hẹp, đồng thời tập đánh giá chưa tách hoàn toàn khỏi quá trình tinh chỉnh. Thứ hai, tải AI mới được thử ngắn hạn trên một máy; chưa có pentest độc lập hay diễn tập khôi phục dài hạn. Thứ ba, hệ thống chưa được xác minh đầy đủ trên thiết bị thật và nghiệp vụ hiện mới hỗ trợ COD. Vì vậy, ba hướng phát triển ưu tiên là: mở rộng dữ liệu thực tế và cải thiện tìm kiếm kết hợp; bổ sung thanh toán, vận chuyển, đổi trả và cá nhân hóa có kiểm soát; cuối cùng là kiểm thử tải phân tán, autoscale, hàng đợi, pentest, quan sát hệ thống và đánh giá với người dùng thật.

**Chuyển sang demo:**

> Sau phần tổng kết, em xin minh họa một luồng sử dụng xuyên suốt từ tìm kiếm đa phương thức đến đặt hàng.

## Slide 27 — Video demo sản phẩm (khoảng 3 phút 50 giây)

Kịch bản quay chi tiết, câu thoại, dữ liệu mẫu và checklist được lưu tại
`presentation/previews/final/kich-ban-quay-video-demo-du-an.md`.

**Lời mở video:**

> Video demo sau minh họa một hành trình xuyên suốt: tìm kiếm bằng văn bản, tìm bằng ảnh, kết hợp ảnh với ràng buộc văn bản, hội thoại nhiều lượt, rồi thêm sản phẩm vào giỏ và đặt hàng COD. Ngoài luồng chính, hệ thống còn có trang yêu thích, bài viết, liên hệ và khu vực quản trị.

**Nhịp demo tóm tắt:**

- 00:00–00:30: giới thiệu trang chủ, danh mục, chi tiết, wishlist, blog và trang thông tin.
- 00:30–01:40: Text Search, Image Search và Hybrid Search.
- 01:40–02:40: hội thoại nhiều lượt để chứng minh bộ nhớ và RAG.
- 02:40–03:31: xem chi tiết, thêm giỏ và đặt COD.
- 03:31–03:52: đối chiếu đơn vừa tạo trong backoffice và kết video.

**Kết video:**

> Video vừa rồi cho thấy các thành phần tìm kiếm, hội thoại và nghiệp vụ mua hàng đã được nối thành một hành trình thống nhất. Sau đây, em xin chuyển sang phần trao đổi.

## Slide 28 — Q&A

> Em xin cảm ơn Hội đồng đã lắng nghe và sẵn sàng trả lời câu hỏi. Khi trao đổi, ưu tiên mở đúng phụ lục theo nhóm câu hỏi: ma trận kiểm thử, hiệu năng, API, lỗi đã khắc phục, YOLO hoặc bản đồ bằng chứng.

## Slide 29 — Tài liệu tham khảo

Không trình bày thành lời nếu không được hỏi. Các mục [1]–[6] là nguồn ngoài cho slide 3 và slide 5; nguồn nội bộ trỏ tới báo cáo cùng các artifact đánh giá.

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
- Khi gần hết giờ, rút ngắn phần số liệu ở slide 23 và phần tổng kết ở slide 25; không bỏ quy trình ba lớp ở slide 22, giới hạn kết luận ở slide 24 hoặc các hạn chế ở slide 26.
