# Bộ câu hỏi và trả lời bảo vệ DATN_HK253

Đề tài: Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision.

Tài liệu luyện trả lời dựa trên slide bảo vệ, nội dung báo cáo và mã nguồn hiện có trong repository. Các câu trả lời dùng ngôi “em”; nếu bảo vệ theo nhóm, đổi thành “nhóm em”. Mỗi câu nên trả lời phần cốt lõi trong 20–40 giây rồi mở rộng khi hội đồng hỏi tiếp. Các kết quả thực nghiệm chỉ có giá trị trên tập dữ liệu, cấu hình và môi trường được ghi nhận.

## A. Bài toán, sản phẩm và đóng góp

### 1. Output của đề tài là gì? ★

Dạ, output chính là một hệ thống web thương mại điện tử thời trang tích hợp trợ lý mua sắm đa phương thức, đã được triển khai thử nghiệm. Người dùng tìm sản phẩm bằng văn bản, hình ảnh hoặc kết hợp cả hai, nhận tư vấn qua hội thoại nhiều lượt rồi tiếp tục xem sản phẩm, thêm giỏ hàng và đặt hàng COD. Các sản phẩm bàn giao còn gồm mã nguồn, tài liệu thiết kế và bộ đánh giá cùng bằng chứng kiểm thử.

### 2. Đề tài giải quyết vấn đề gì? ★

Dạ, người mua có thể không biết tên chính xác của sản phẩm, chỉ có ảnh tham chiếu hoặc mô tả nhu cầu. Họ cũng thường bổ sung yêu cầu qua nhiều lượt như đổi màu, đổi size hoặc giảm ngân sách. Đề tài xử lý việc tìm sản phẩm từ các đầu vào đó và duy trì ngữ cảnh để tư vấn dựa trên dữ liệu catalog.

### 3. Tại sao chọn lĩnh vực thời trang?

Dạ, thời trang có nhu cầu tìm bằng hình ảnh rõ rệt, đồng thời có các thuộc tính như màu, chất liệu, size và giá để kiểm tra khả năng hiểu ràng buộc. Em giới hạn một lĩnh vực để chuẩn hóa dữ liệu và xây dựng bộ đánh giá có thể kiểm soát trong phạm vi đồ án.

### 4. Đóng góp chính của em là gì? ★

Dạ, đóng góp gồm xây dựng pipeline tìm kiếm đa phương thức, hội thoại RAG có bộ nhớ và tích hợp chúng với dữ liệu nghiệp vụ hiện hành. Em còn chuẩn hóa dữ liệu, fine-tune YOLO cho các nhóm sản phẩm thời trang và thực hiện đối chứng, ablation để chọn cấu hình. Đóng góp được thể hiện ở giải pháp tích hợp và kết quả đánh giá trong phạm vi bài toán này.

### 5. Đề tài có tính mới ở đâu khi các mô hình đều có sẵn? ★

Dạ, em sử dụng các mô hình nền có sẵn; phần em xây dựng là cách phối hợp truy hồi, xử lý ràng buộc, quản lý ngữ cảnh và xác minh dữ liệu nghiệp vụ. Ví dụ, ảnh tạo ứng viên theo hình dáng, văn bản áp dụng yêu cầu cụ thể, rồi Backend cung cấp thông tin sản phẩm hiện hành. Em không tuyên bố tạo ra mô hình nền hay thuật toán mới trên phạm vi toàn ngành.

### 6. So với website bán hàng thông thường, hệ thống có gì khác?

Dạ, người dùng có thể mô tả nhu cầu tự nhiên, tải ảnh tham chiếu và tiếp tục tinh chỉnh bằng hội thoại. Điểm trọng tâm là nối quá trình tìm và tư vấn sản phẩm với luồng mua sắm, đồng thời kiểm soát dữ kiện bằng catalog và Backend.

### 7. So với Google Lens hoặc các sàn thương mại điện tử thì sao?

Dạ, phạm vi của em là catalog thời trang cụ thể và hành trình mua sắm trong hệ thống đó. Em tập trung kết hợp ảnh, ràng buộc văn bản và hội thoại nhiều lượt với nghiệp vụ. Em chưa có benchmark trực tiếp trên cùng dữ liệu với các sản phẩm thương mại, nên không kết luận hệ thống tốt hơn họ.

### 8. Ai sử dụng hệ thống và phạm vi đã hoàn thành đến đâu?

Dạ, khách hàng dùng chức năng tìm kiếm, tư vấn, giỏ hàng và đặt hàng COD; quản trị viên quản lý sản phẩm, tồn kho, đơn hàng và nội dung. Hệ thống đang ở mức nguyên mẫu triển khai thử nghiệm. Thanh toán trực tuyến, tích hợp vận chuyển, đổi trả và hoàn tiền là các hướng bổ sung.

## B. Kiến trúc và dữ liệu

### 9. Trình bày kiến trúc hệ thống trong một phút. ★

Dạ, React cung cấp giao diện; Spring Boot xử lý xác thực, phân quyền và nghiệp vụ với MySQL; FastAPI điều phối tìm kiếm và trợ lý AI; Qdrant lưu vector cùng metadata phục vụ truy hồi. Trình duyệt gọi Backend, Backend giao tiếp với AI Service khi cần. MySQL là nguồn dữ liệu chuẩn, còn Qdrant là chỉ mục dẫn xuất có thể tái tạo.

### 10. Tại sao tách Backend nghiệp vụ và AI Service?

Dạ, Spring Boot phù hợp với nghiệp vụ có transaction, còn Python thuận tiện cho xử lý ảnh và tích hợp mô hình. Tách dịch vụ giúp thay đổi hoặc triển khai phần AI độc lập và giữ nghiệp vụ lõi hoạt động khi AI gián đoạn. Đổi lại, em phải kiểm soát hợp đồng API, timeout, retry và theo dõi request giữa hai dịch vụ.

### 11. Tại sao dùng cả MySQL và Qdrant? ★

Dạ, MySQL lưu dữ liệu quan hệ và giao dịch như tài khoản, tồn kho và đơn hàng. Qdrant phục vụ tìm kiếm tương đồng vector và lọc metadata. Mỗi hệ giải quyết một nhu cầu; Qdrant không quyết định giá cuối cùng, tồn kho hay trạng thái đơn hàng.

### 12. Tại sao chọn Qdrant?

Dạ, Qdrant hỗ trợ truy hồi vector, cosine similarity, HNSW, payload filtering và triển khai bằng Docker, phù hợp với catalog hiện tại. Em chọn dựa trên khả năng tích hợp và kiểm soát vận hành của đề tài; chưa thực hiện benchmark đầy đủ để khẳng định nó tốt nhất so với mọi vector database.

### 13. Dữ liệu sản phẩm lấy từ đâu? ★

Dạ, dữ liệu được thu thập từ website Zara, gồm tên, mô tả, ảnh, màu, chất liệu, danh mục và các thuộc tính liên quan. Em dùng Qwen3.5-9B hỗ trợ Việt hóa, giữ các thông tin tiếng Anh cần thiết rồi rà soát, chuẩn hóa. Catalog chính thức của đồ án gồm 1.000 sản phẩm, được khởi tạo từ tệp 1000_final.sql.

### 14. Dữ liệu do LLM dịch có đáng tin không?

Dạ, dịch tự động có thể sai thuật ngữ hoặc làm thay đổi thuộc tính. Vì vậy em giữ thông tin nguồn và có bước rà soát, chuẩn hóa thay vì coi bản dịch là ground truth mặc định. Sai sót còn lại trong metadata là một giới hạn có thể ảnh hưởng cả retrieval và đánh giá ràng buộc.

### 15. Khi sản phẩm đổi giá, AI có trả thông tin cũ không? ★

Dạ, chỉ mục vector có thể chậm đồng bộ so với MySQL. Vì vậy kết quả truy hồi được quy về mã sản phẩm, rồi Backend đọc dữ liệu hiện hành để hiển thị và xử lý nghiệp vụ. Cơ chế này giảm rủi ro hiển thị dữ liệu cũ, nhưng metadata cũ vẫn có thể ảnh hưởng bước chọn ứng viên; do đó vẫn cần đồng bộ và đối soát chỉ mục.

### 16. Đồng bộ MySQL–Qdrant có transaction chung không?

Dạ, hai hệ không dùng một transaction ACID chung. Giao dịch nghiệp vụ commit ở MySQL, sau đó chỉ mục được cập nhật; lỗi indexing được ghi nhận để thử lại. Đây là tính nhất quán cuối cùng, với MySQL giữ vai trò nguồn chuẩn. Khi cần có thể full sync hoặc tái tạo chỉ mục.

### 17. Retry có gây trùng dữ liệu không?

Dạ, đồng bộ dùng product_id để xác định dữ liệu cần thay thế; cập nhật loại bỏ vector cũ của sản phẩm rồi lập chỉ mục dữ liệu hiện tại. Các ca retry đã kiểm tra việc không tạo point trùng. Tuy nhiên, delete rồi upsert có thể tạo khoảng trống tạm thời khi lỗi; retry và đối soát giúp phục hồi trạng thái đó.

## C. Tìm kiếm văn bản, ảnh và kết hợp

### 18. Embedding là gì và dùng để làm gì? ★

Dạ, embedding biểu diễn văn bản hoặc hình ảnh thành vector số, để hệ thống so sánh mức độ tương đồng. Sản phẩm được embedding khi indexing; truy vấn được embedding lúc tìm kiếm. Sau đó Qdrant truy hồi các ứng viên gần với vector truy vấn, kết hợp bộ lọc và các tín hiệu xếp hạng.

### 19. Cosine similarity có phải xác suất sản phẩm phù hợp không?

Dạ, không. Nó là độ tương đồng về hướng giữa các vector trong không gian biểu diễn của mô hình. Điểm cao là tín hiệu để xếp hạng, không phải xác suất người dùng thích hay mua sản phẩm, và không tự bảo đảm sản phẩm thỏa giá, màu hoặc size.

### 20. Tìm kiếm ngữ nghĩa khác tìm kiếm từ khóa thế nào?

Dạ, tìm kiếm từ khóa dựa nhiều vào sự trùng khớp từ, còn embedding hỗ trợ tìm nội dung gần về ý nghĩa khi cách diễn đạt khác nhau. Tuy nhiên, từ khóa vẫn hữu ích với tên chính xác, mã hoặc thuộc tính cụ thể. Bản triển khai GCP kết hợp vector với tín hiệu lexical và metadata cho Text Search.

### 21. Image Search chạy như thế nào? ★

Dạ, hệ thống nhận và kiểm tra ảnh; phát hiện vùng sản phẩm bằng YOLO khi được bật hoặc dùng vùng người dùng chọn; crop, chuẩn hóa rồi tạo embedding ảnh. Qdrant tìm vector ảnh tương đồng và kết quả được quy về sản phẩm để Backend bổ sung dữ liệu hiện hành. Nếu không có vùng phát hiện phù hợp, hệ thống dùng ảnh đầy đủ.

### 22. YOLO có trực tiếp tìm ra sản phẩm trong catalog không? ★

Dạ, YOLO chỉ phát hiện vị trí và nhóm vật thể để chọn vùng ảnh cần tìm. Việc tìm sản phẩm tương tự trong catalog do embedding và vector retrieval thực hiện. Phân biệt hai vai trò này giúp đánh giá riêng chất lượng detector và chất lượng tìm kiếm.

### 23. Em có tự huấn luyện mô hình nào không?

Dạ, em fine-tune YOLOv26s từ weight pretrained trên dữ liệu thời trang xây dựng từ Fashionpedia. Nhãn được gom thành bốn lớp: accessories, bags, clothing và shoes. Các mô hình embedding và LLM được sử dụng từ mô hình có sẵn, không được em huấn luyện từ đầu.

### 24. Kết quả fine-tune YOLO ra sao?

Dạ, báo cáo ghi nhận Precision 0,875, Recall 0,760, mAP50 0,849 và mAP50–95 0,685. Clothing và shoes có mAP50 cao hơn accessories; vật thể phụ kiện nhỏ là điểm khó. Các số này đo khả năng phát hiện vùng vật thể, không phải độ chính xác Image Search.

### 25. YOLO không phát hiện hoặc crop sai thì làm sao?

Dạ, nếu không có vùng phù hợp, hệ thống fallback sang ảnh gốc. Giao diện cũng hỗ trợ chọn hoặc điều chỉnh vùng sản phẩm. Crop sai vẫn có thể làm retrieval kém đi; để chứng minh lợi ích riêng của YOLO cần ablation bật/tắt crop trên cùng bộ truy vấn, không suy từ mAP detector sang chất lượng tìm kiếm.

### 26. Hybrid Search kết hợp ảnh và văn bản như thế nào? ★

Dạ, cấu hình được chọn là image-conditioned: ảnh tạo ứng viên và quyết định độ tương tự trực quan; văn bản cung cấp ràng buộc và thuộc tính ưu tiên. Kết quả chủ yếu xếp theo điểm ảnh; nhánh văn bản hỗ trợ phục hồi khi thiếu ứng viên. Cấu hình vận hành này không cộng trọng số điểm text và image theo kiểu fusion.

### 27. Ví dụ “giống ảnh này nhưng màu đen, dưới 800 nghìn” xử lý thế nào?

Dạ, ảnh giúp tìm sản phẩm có hình dáng tương tự, còn màu đen và ngân sách là yêu cầu văn bản cần được kiểm tra. Pipeline cần phân biệt yêu cầu rõ ràng với thuộc tính chỉ suy đoán, rồi đối chiếu metadata. Nếu không có sản phẩm đáp ứng, hệ thống thông báo hoặc hỏi lại, tránh trình bày sản phẩm vi phạm như đáp án đúng.

### 28. Nếu không có kết quả, có tự bỏ bộ lọc không?

Dạ, các bộ lọc người dùng truyền rõ ràng là điều kiện bắt buộc và không được tự nới lỏng. Một số điều kiện suy luận có thể dùng làm tín hiệu xếp hạng hoặc được bỏ trong nhánh recovery theo cấu hình. Hệ thống cần giữ nguồn gốc điều kiện và thể hiện cảnh báo khi phục hồi kết quả.

### 29. Vì sao chọn image-conditioned thay vì fusion? ★

Dạ, trên 100 truy vấn paired, image-conditioned không rerank đạt Strict Hit@5 là 0,980, NDCG theo yêu cầu là 0,958 và thỏa ràng buộc là 0,990. So với fusion, cấu hình này đáp ứng yêu cầu cụ thể tốt hơn, dù NDCG tổng quát thấp hơn và độ trễ cao hơn. Em chọn theo mục tiêu đúng ảnh và đúng ràng buộc, với độ trễ vẫn đạt gate.

### 30. Vì sao tắt reranker? ★

Dạ, ablation hybrid cho thấy bật rerank làm Strict Hit@5 giảm từ 0,980 xuống 0,730, trong khi thỏa ràng buộc chỉ tăng từ 0,990 lên 0,992 và độ trễ tăng. RAG cũng không ghi nhận lợi ích trên các chỉ số chính. Vì vậy em tắt rerank ở cấu hình được chọn; em chỉ kết luận cho mô hình và dữ liệu đã thử nghiệm.

### 31. Vì sao tách collection văn bản và hình ảnh?

Dạ, hai collection giúp quản lý embedding và truy hồi từng modality độc lập, rồi liên kết bằng product_id. Trên GCP, vector text và ảnh còn có số chiều khác nhau nên không thể trực tiếp dùng chung một không gian vector. Kết hợp diễn ra ở ứng viên, metadata và chính sách xếp hạng.

### 32. Đổi mô hình embedding có dùng lại vector cũ không? ★

Dạ, không nên dùng lại vì không gian biểu diễn thay đổi, kể cả khi số chiều giống nhau. Em phải tạo collection phù hợp, embedding lại sản phẩm và kiểm tra trước khi chuyển truy vấn sang chỉ mục mới. Giữ collection cũ giúp rollback.

## D. RAG, LLM và bộ nhớ hội thoại

### 33. RAG là gì và vì sao dùng trong đề tài? ★

Dạ, RAG truy xuất dữ liệu liên quan rồi đưa vào context để LLM sinh câu trả lời. Với đề tài này, nguồn là chỉ mục sản phẩm và dữ liệu nghiệp vụ từ Backend. Nó giúp trợ lý tư vấn dựa trên catalog cụ thể, thay vì dựa hoàn toàn vào kiến thức sẵn có của mô hình.

### 34. LLM làm phần nào, Backend làm phần nào?

Dạ, LLM hỗ trợ hiểu ý định, viết lại truy vấn, trích xuất điều kiện và diễn đạt tư vấn. Backend kiểm soát giá, tồn kho, phân quyền và giao dịch. Đầu ra LLM phải được kiểm tra cấu trúc; LLM không được tự quyết định giá cuối, sinh mã sản phẩm không tồn tại hay thực hiện giao dịch tùy ý.

### 35. RAG có bảo đảm không hallucination không? ★

Dạ, RAG giúp giảm rủi ro nhưng không bảo đảm tuyệt đối. Em kết hợp truy hồi, dữ liệu hiện hành, prompt giới hạn nguồn, kiểm tra đầu ra và phản hồi khi thiếu dữ liệu. Grounding đạt 1,000 trên tập kiểm thử không đồng nghĩa mọi câu hỏi ngoài thực tế đều không có phát biểu sai.

### 36. Nếu catalog không có thông tin người dùng hỏi thì sao?

Dạ, trợ lý cần nói rõ chưa có dữ liệu hoặc hỏi làm rõ, tránh suy đoán như một dữ kiện đã xác nhận. Ví dụ thiếu thông tin chất liệu thì không được khẳng định một sản phẩm là cotton chỉ từ hình ảnh. Giá trị của trợ lý nằm ở câu trả lời có căn cứ và biết giới hạn dữ liệu.

### 37. Vì sao cần memory nếu đã có RAG? ★

Dạ, RAG cung cấp dữ kiện sản phẩm, còn memory giữ yêu cầu và tham chiếu của người dùng qua nhiều lượt. Ví dụ “đổi sang màu đen” cần biết sản phẩm hoặc loại sản phẩm đang nói đến. Memory lưu các ràng buộc còn hiệu lực, lịch sử gần, tóm tắt và các danh sách sản phẩm đã được đề cập.

### 38. Người dùng đổi ý thì ưu tiên thông tin nào?

Dạ, sửa đổi rõ ràng ở lượt mới thay thế giá trị cũ của cùng thuộc tính; những điều kiện khác vẫn được giữ nếu chưa bị thay đổi. Chẳng hạn đổi ngân sách từ 800 nghìn lên 1 triệu thì ngân sách mới có hiệu lực. Sở thích dài hạn chỉ là tín hiệu mềm và không được lấn át yêu cầu hiện tại.

### 39. “Cái thứ hai lúc đầu” và “cái thứ hai vừa rồi” có phân biệt được không?

Dạ, hệ thống lưu các mốc danh sách ứng viên và nguồn tham chiếu để phân biệt danh sách ở các lượt. Nếu xác định được danh sách, vị trí được ánh xạ về product_id tương ứng. Nếu tham chiếu không rõ, hệ thống hỏi lại thay vì chọn một sản phẩm gần đúng.

### 40. Có đưa toàn bộ lịch sử hội thoại vào prompt không?

Dạ, không. Em giới hạn lịch sử gần, kết hợp tóm tắt và trạng thái có cấu trúc để kiểm soát token, chi phí và độ trễ. Việc tóm tắt có nguy cơ mất chi tiết, nên các ràng buộc và tham chiếu sản phẩm quan trọng cần được giữ riêng và kiểm thử bằng hội thoại dài.

### 41. Làm sao tránh lẫn bộ nhớ giữa người dùng?

Dạ, checkpoint được phân tách theo người dùng và phiên; hồ sơ sở thích dài hạn được tách riêng theo định danh người dùng. Backend xác định tài khoản từ phiên xác thực, không tin tùy ý user_id phía client. Bộ nhớ có giới hạn, TTL và chức năng xóa sở thích.

### 42. Vì sao dùng LangGraph?

Dạ, workflow có nhiều bước và nhánh: hiểu truy vấn, định tuyến, truy hồi, lấy dữ liệu sản phẩm, hỏi làm rõ và sinh phản hồi. LangGraph giúp biểu diễn trạng thái cùng điều kiện chuyển bước rõ ràng để kiểm thử. Em dùng workflow có giới hạn, không trao quyền thao tác nghiệp vụ tùy ý cho mô hình.

### 43. Memory của bản GCP có bền vững không? ★

Dạ, đây là một hạn chế của bản demo. Hồ sơ sở thích dài hạn dùng Memorystore, nhưng checkpoint LangGraph đang dùng SQLite trên filesystem tạm vì cấu hình Memorystore không có RedisJSON. Khi instance dừng, checkpoint phiên có thể mất. Muốn vận hành dài hạn cần chuyển checkpoint sang PostgreSQL hoặc kho bền vững tương thích và kiểm thử lại.

## E. Thực nghiệm và cách giải thích số liệu

### 44. Em đánh giá trên bộ dữ liệu nào? ★

Dạ, catalog có 1.000 sản phẩm. Text Search có 100 truy vấn gồm 90 dương và 10 âm; Image Search có 100 ảnh catalog và 100 ảnh bên ngoài ghép cặp theo cùng 100 sản phẩm; Hybrid có 100 truy vấn. Hội thoại có bộ 80 câu và 12 ca critical, cùng kiểm thử phiên dài. Mỗi nhóm có ground truth và cách tính metric riêng.

### 45. Ground truth được xây dựng thế nào?

Dạ, em đóng băng snapshot, pooling ứng viên từ các cấu hình và duyệt mức liên quan từ 0 đến 3. Metric nhị phân dùng ngưỡng liên quan từ 2, còn NDCG giữ nhãn nhiều mức. Với ảnh, exact metric đối chiếu product_id nguồn; với hybrid, ràng buộc được tính độc lập từ câu hỏi và snapshot, không lấy nguyên kết luận của API làm đáp án.

### 46. Hit@5 bằng 1 có nghĩa cả năm sản phẩm đều đúng không? ★

Dạ, không. Nó nghĩa là mỗi truy vấn được tính có ít nhất một sản phẩm liên quan trong năm kết quả đầu. Text Hit@5 bằng 1,000 áp dụng cho 90 truy vấn dương. Muốn biết tỷ lệ đúng của cả danh sách cần Precision@5; chất lượng thứ hạng cần NDCG@5.

### 47. NDCG, Precision, Recall và MRR khác nhau thế nào?

Dạ, Precision đo tỷ lệ kết quả trả về có liên quan; Recall đo mức bao phủ các sản phẩm liên quan trong ground truth; MRR phản ánh thứ hạng của kết quả đúng đầu tiên. NDCG xét cả mức liên quan và vị trí, nên sản phẩm phù hợp cao xuất hiện đầu danh sách được đánh giá tốt hơn. Recall cần diễn giải theo giới hạn của ground truth đã pooling.

### 48. Strict Hit@5 và tỷ lệ thỏa ràng buộc khác nhau thế nào?

Dạ, Strict Hit@5 đánh giá ở cấp truy vấn: có ít nhất một kết quả phù hợp theo tiêu chí strict trong Top-5 hay không. Tỷ lệ thỏa ràng buộc đánh giá các kết quả theo điều kiện được người dùng nêu. Vì vậy một truy vấn có kết quả đúng trong Top-5 vẫn có thể có nhiều sản phẩm vi phạm điều kiện; phải xem đồng thời hai chỉ số.

### 49. NDCG theo yêu cầu khác NDCG thông thường thế nào?

Dạ, NDCG theo yêu cầu giữ nhãn relevance nhưng đặt gain bằng 0 nếu sản phẩm vi phạm ràng buộc của truy vấn. Nó giúp phân biệt sản phẩm nhìn chung tương tự với sản phẩm thực sự đáp ứng yêu cầu hiện tại. Đây là lý do image-conditioned có thể tốt hơn theo yêu cầu dù NDCG tổng quát thấp hơn fusion.

### 50. Grounding 1,000 có nghĩa trợ lý hoàn hảo không? ★

Dạ, không. Grounding đo mức hỗ trợ của context đối với khẳng định theo scorer và bộ đánh giá đã dùng. Nó không tự chứng minh dữ liệu nguồn luôn đúng, tư vấn luôn hữu ích hoặc mọi truy vấn mới đều được xử lý chính xác. Em kết hợp Context Precision, Context Recall, hard gate và phân tích các tình huống khó.

### 51. Có bằng chứng RAG và memory thực sự cải thiện không? ★

Dạ, trong bảng ablation của báo cáo, LLM không RAG đạt Grounding 0,824 và 4/12 ca critical; thêm RAG đạt Grounding 1,000 và 12/12 ca. Thêm memory tăng Context Precision từ 0,882 lên 0,946 và Context Recall từ 0,879 lên 0,944. Kết quả hỗ trợ vai trò hai thành phần trên bộ đánh giá hiện có, không phải bảo đảm cho mọi hội thoại.

### 52. Vì sao không dùng Token-F1 để kết luận chatbot tốt?

Dạ, một câu trả lời đúng có thể diễn đạt khác câu tham chiếu nên Token-F1 thấp; ngược lại, câu gần từ vựng vẫn có thể sai dữ kiện. Vì thế em dùng nó để chẩn đoán, còn tiêu chí chính là grounding, context và các ca critical. Tính hữu ích với người dùng thực vẫn cần nghiên cứu riêng.

### 53. Kết quả tìm kiếm chính là gì? ★

Dạ, Text Search đạt Hit@5 1,000 và NDCG@5 khoảng 0,941. Image Search đạt Exact Hit@5 1,000 với ảnh catalog và 0,970 với ảnh bên ngoài; NDCG tương ứng 0,853 và 0,810. Hybrid được chọn đạt Strict Hit@5 0,980, NDCG theo yêu cầu 0,958 và thỏa ràng buộc 0,990. Đây là các số liệu thực nghiệm trong báo cáo, cần gắn với cấu hình đã đo.

### 54. Em so sánh với baseline nào?

Dạ, Text Search so với BM25 và kiểm tra bật/tắt rerank; Hybrid so với text-only, image-only, fusion và image-conditioned bật/tắt rerank. Hội thoại so sánh LLM không RAG, RAG không memory và RAG có memory. Image Search dùng ảnh catalog và ảnh bên ngoài theo cặp để đo độ bền; so sánh đó chưa phải đối chứng giữa các thuật toán embedding.

### 55. Mức cải thiện Text Search cụ thể là bao nhiêu?

Dạ, trên cùng 90 truy vấn dương, BM25 đạt Hit@5 khoảng 0,756 và NDCG@5 khoảng 0,689; vector không rerank đạt 1,000 và 0,941. Chênh lệch Hit@5 là khoảng 24,44 điểm phần trăm. Kết quả này chứng minh lợi ích trên bộ truy vấn đó; tên sản phẩm chính xác hoặc catalog khác có thể cho kết quả khác.

### 56. Bootstrap và khoảng tin cậy có ý nghĩa gì?

Dạ, paired bootstrap lấy mẫu lại các cặp truy vấn để ước lượng độ biến thiên của chênh lệch giữa hai cấu hình. Hybrid dùng 10.000 lần lấy mẫu với seed 42. Khoảng tin cậy 95% không chứa 0 hỗ trợ nhận định có chênh lệch trên tập thử, nhưng không loại bỏ thiên lệch của dữ liệu hay ground truth.

### 57. Điểm cao như vậy có nguy cơ thiên lệch hoặc overfitting không? ★

Dạ, có. Catalog và số truy vấn còn nhỏ; ảnh catalog gần dữ liệu đã index, và tập đánh giá chưa hoàn toàn độc lập với quá trình điều chỉnh cấu hình. Em có ảnh bên ngoài, baseline và ablation để kiểm tra thêm, nhưng chưa coi các điểm này là khả năng tổng quát ngoài thực tế. Bước tiếp theo là tách tập điều chỉnh và tập kiểm thử độc lập, mở rộng dữ liệu.

### 58. Ground truth pooling có hạn chế gì?

Dạ, pooling chỉ duyệt các ứng viên được những cấu hình hiện có tìm ra, nên có thể bỏ sót sản phẩm phù hợp ngoài pool. Điều đó ảnh hưởng cách diễn giải Recall, mAP và so sánh với phương pháp mới. Em cần công bố cách pooling và mở rộng nhãn khi bổ sung thuật toán mới.

### 59. Kết quả ảnh ngoài giảm chứng tỏ điều gì?

Dạ, nó cho thấy pipeline nhạy với nền, góc chụp và người mẫu. Exact Hit@1 giảm từ 0,980 xuống 0,930, trong khi Exact Hit@5 giảm từ 1,000 xuống 0,970. Hệ thống vẫn thường tìm được sản phẩm nguồn trong Top-5, nhưng xếp đúng vị trí đầu còn khó hơn trên ảnh ngoài.

### 60. Các kết quả local có áp dụng nguyên cho GCP không? ★

Dạ, không thể chuyển nguyên kết luận vì mô hình embedding, chỉ mục và hạ tầng khác nhau. Bộ kết quả định lượng cần được gắn với cấu hình thực nghiệm tương ứng; smoke test GCP xác nhận triển khai và luồng hoạt động. Muốn kết luận chất lượng GCP tương đương phải chạy lại cùng bộ đánh giá trên bản GCP.

## F. Nghiệp vụ, an toàn và vận hành

### 61. Ngoài AI, em đã kiểm thử những gì?

Dạ, em kiểm tra API và nghiệp vụ, hợp đồng Backend–AI Service, đồng bộ MySQL–Qdrant, retry, rollback và các luồng end-to-end. Báo cáo ghi nhận 102/102 ca Backend và năm hành trình end-to-end đạt. Đây là độ bao phủ các ca đã xây dựng; không suy ra phần mềm không còn lỗi.

### 62. Hai người cùng mua sản phẩm cuối cùng thì sao?

Dạ, quyết định cấp tồn kho được xử lý ở Backend trong giao dịch, không dựa vào số lượng hiển thị trên giao diện hay câu trả lời AI. Kiểm thử đã tạo hai request cạnh tranh SKU cuối và đối soát việc cấp tồn kho đúng một lần. Khi lỗi, giao dịch phải rollback; khi cần trình bày cơ chế khóa cụ thể em mở phần triển khai checkout.

### 63. Retry đặt hàng có tạo hai đơn không?

Dạ, retry thao tác ghi cần cơ chế idempotency; thiết kế không cho tự retry checkout khi chưa có idempotency key. Em phân biệt retry tìm kiếm hoặc đồng bộ với retry giao dịch. Khi hội đồng hỏi về endpoint cụ thể, cần đối chiếu mã nguồn và test của endpoint đó, không khẳng định mọi API ghi đều đã có idempotency.

### 64. AI Service lỗi thì website có ngừng hoạt động không? ★

Dạ, catalog, giỏ hàng và đơn hàng vẫn được phục vụ bởi Backend và MySQL. Tìm kiếm AI hoặc tư vấn có thể suy giảm hoặc báo lỗi theo fallback, nhưng lỗi không lan sang nghiệp vụ lõi. Các luồng fallback khi AI gián đoạn đã được kiểm thử trong phạm vi đồ án.

### 65. Nếu Qdrant mất dữ liệu thì làm sao?

Dạ, có thể khôi phục snapshot hoặc tạo lại chỉ mục từ MySQL rồi embedding lại sản phẩm. Việc này cần thời gian và chi phí mô hình, nên vẫn phải backup và kiểm tra phục hồi. Trong lúc phục hồi, nghiệp vụ lõi có thể tiếp tục, còn tìm kiếm vector bị ảnh hưởng.

### 66. Hệ thống bảo mật như thế nào?

Dạ, Backend xác thực bằng JWT, kiểm tra vai trò và quyền sở hữu tài nguyên; API nội bộ có khóa riêng. Đầu vào và ảnh tải lên được kiểm tra, secret được quản lý bên ngoài mã nguồn, log hạn chế dữ liệu nhạy cảm. Các ca token sai, sai quyền và dữ liệu nguy hiểm đã được kiểm tra; kết quả này chưa thay thế pentest độc lập.

### 67. Prompt injection đã được giải quyết triệt để chưa?

Dạ, chưa thể khẳng định triệt để. Thiết kế giới hạn tác vụ LLM, coi nội dung người dùng và dữ liệu truy xuất là dữ liệu không đáng tin, kiểm tra đầu ra và giữ quyền giao dịch ở Backend. Để chứng minh độ bền trước prompt injection cần bộ kiểm thử đối kháng riêng; các test bảo mật web thông thường chưa đủ để kết luận.

### 68. P95 là gì? Có phải thời gian trung bình không?

Dạ, P95 là phân vị 95: khoảng 95% thời gian phản hồi trong mẫu không vượt giá trị đó. Nó giúp quan sát độ trễ ở phần đuôi tốt hơn trung bình, nhưng vẫn còn khoảng 5% mẫu chậm hơn. Cần nói rõ endpoint, workload và môi trường khi nêu P95.

### 69. 57.600 request trong hai giờ có nghĩa chịu được 57.600 người dùng không? ★

Dạ, không. Đây là tổng số request hoàn thành trong bài soak hai giờ, tương đương trung bình tám request mỗi giây. Số người dùng đồng thời phụ thuộc workload, tốc độ thao tác và cơ chế sinh tải. Bài này hỗ trợ đánh giá ổn định theo workload đã định nghĩa, không chứng minh sức tải của mọi endpoint hoặc của AI.

### 70. Triển khai GCP dùng những mô hình nào? ★

Dạ, bản GCP dùng Qwen3-Embedding-8B cho text với vector 4.096 chiều, Qwen3-VL-Embedding-2B cho ảnh với vector 2.048 chiều và YOLO trên GPU. LLM được gọi qua Bedrock với model openai.gpt-oss-120b-1:0. Môi trường local dùng Cohere Embed v4 qua Bedrock cho embedding 1.536 chiều, nên collection của hai môi trường được tách riêng.

### 71. Hệ thống trên GCP triển khai ra sao?

Dạ, GCE chạy Frontend, Backend, MySQL và Qdrant; AI Service chạy trên Cloud Run GPU. Cấu hình demo giới hạn tối đa một instance và concurrency bằng một, nên chưa chứng minh autoscale hay phục vụ tải lớn. Sau nghiệm thu, GPU được cấu hình scale-to-zero để giảm thời gian giữ tài nguyên.

### 72. Chi phí triển khai là bao nhiêu?

Dạ, báo cáo ghi nhận chi phí build, giữ GPU để đồng bộ và kiểm thử khoảng 5,5–7 USD, chưa gồm phí Bedrock nhỏ. Đây là chi phí của đợt thử nghiệm đã ghi nhận, không phải giá vận hành một tháng. Ước lượng dài hạn cần số request, token, thời gian GPU hoạt động, VM, lưu trữ và mạng thực tế.

### 73. Hệ thống có production-ready chưa? ★

Dạ, chưa. Hệ thống đạt nghiệm thu nội bộ trong phạm vi đồ án và có bản triển khai thử nghiệm. Để vận hành thương mại cần dữ liệu và kiểm thử độc lập rộng hơn, kiểm thử tải dài hạn, pentest, checkpoint bền vững, giám sát, phục hồi và bổ sung các nghiệp vụ thanh toán, vận chuyển, đổi trả.

### 74. Nếu tăng lên một triệu sản phẩm thì có chạy được không?

Dạ, kiến trúc có thể là nền tảng để mở rộng, nhưng em chưa đo ở quy mô đó nên chưa khẳng định sức tải. Cần đánh giá bộ nhớ chỉ mục, số vector ảnh, tốc độ indexing, tham số ANN, độ chọn lọc của filter và throughput mô hình. Bước mở rộng cần workload thực tế và benchmark theo từng quy mô.

### 75. Hạn chế lớn nhất và hướng ưu tiên là gì? ★

Dạ, hạn chế chính là dữ liệu và tập đánh giá còn nhỏ, chưa hoàn toàn độc lập với quá trình tinh chỉnh; ảnh ngoài làm giảm độ bền và triển khai demo còn giới hạn về tải, checkpoint. Em ưu tiên mở rộng, tách tập đánh giá độc lập và cải thiện chất lượng truy hồi trước. Sau đó củng cố lưu trạng thái, vận hành, bảo mật và đánh giá với người dùng thực.

### 76. Em có chứng minh hệ thống giúp tăng doanh thu hoặc giảm thời gian mua hàng chưa?

Dạ, chưa. Hiện em đo chất lượng truy hồi, căn cứ phản hồi và tính đúng đắn của hệ thống. Tăng doanh thu, giảm thời gian tìm hoặc mức hài lòng cần nghiên cứu với người dùng thực hoặc A/B test có thiết kế phù hợp. Đây là giá trị kỳ vọng cần xác minh, không phải kết quả đã đạt.

### 77. Phần nào em tự làm, phần nào dùng công cụ có sẵn? ★

Dạ, các mô hình nền, framework và dịch vụ cloud là thành phần có sẵn. Phần tự xây dựng gồm ứng dụng nghiệp vụ, pipeline dữ liệu và đồng bộ, tìm kiếm, workflow hội thoại, tích hợp và bộ kiểm thử; YOLO được fine-tune cho phạm vi thời trang. Nếu thực hiện theo nhóm, em trình bày đúng phần việc cá nhân và dẫn mã nguồn, commit hoặc artifact tương ứng.

### 78. Nếu được làm lại, em sẽ thay đổi điều gì?

Dạ, em sẽ tách bộ dữ liệu điều chỉnh và kiểm thử độc lập ngay từ đầu, chuẩn hóa metadata sớm và đặt checkpoint bền vững cho môi trường cloud. Em cũng sẽ bổ sung ablation riêng cho crop ảnh và đánh giá với người dùng thực. Các thay đổi này giúp kết quả đáng tin hơn và giảm rủi ro khi triển khai.

## G. Câu hỏi bổ sung từ slide bảo vệ, báo cáo và mã nguồn

### 79. Vì sao slide ghi 17 yêu cầu chức năng và 9 yêu cầu phi chức năng? ★

Dạ, bộ yêu cầu chi tiết được nhóm thành 12 yêu cầu AI, 5 yêu cầu thương mại điện tử và 9 NFR về hiệu năng, bảo mật, khả dụng, đúng đắn, bảo trì, tương thích, quan sát, đồng bộ chỉ mục và chất lượng AI. Việc chia nhóm giúp truy vết từ yêu cầu đến test và bằng chứng, không có nghĩa 17 màn hình hay 17 API. Khi dẫn mã yêu cầu, em dùng đúng mã trong bảng truy vết của bản báo cáo đang trình bày.

### 80. Bốn câu hỏi nghiên cứu của đề tài là gì?

Dạ, RQ1 hỏi chất lượng Text, Image và Hybrid Search; RQ2 hỏi RAG và memory có cải thiện tính có căn cứ và ngữ cảnh hội thoại không; RQ3 hỏi nghiệp vụ, giao tiếp dịch vụ và đồng bộ có bảo toàn trạng thái không; RQ4 hỏi các yêu cầu phi chức năng đạt đến đâu. Mỗi RQ được đối chiếu với một nhóm kiểm thử riêng, nên kết luận không chỉ dựa vào demo giao diện.

### 81. Yêu cầu nào chưa đạt đầy đủ? ★

Dạ, NFR-06 về tương thích trình duyệt chỉ đạt một phần. Bộ Playwright ghi nhận 8/8 ca trên Firefox và WebKit, nhưng chưa có đầy đủ artifact tự động cho Chrome, Edge hoặc Safari trên thiết bị Apple thật. Em không diễn giải WebKit là đã kiểm thử Safari thực tế.

### 82. Slide ghi mục tiêu nghiệp vụ 1–3 giây, AI 2–5 giây. Gate chính thức là gì?

Dạ, đó là khoảng thời gian mục tiêu trình bày ngắn trên slide. Bảng yêu cầu trong báo cáo dùng ngưỡng nghiệm thu P95 không quá 3 giây cho API nghiệp vụ, không quá 5 giây cho chức năng AI và tỷ lệ lỗi không quá 1%. Khi trả lời kết quả, em viện dẫn đúng gate, endpoint và workload tương ứng.

### 83. “Ba tác nhân” trong use case gồm ai? AI Service có phải người dùng không?

Dạ, đó là khách hàng, quản trị viên và AI Service. AI Service là tác nhân hệ thống hỗ trợ truy hồi, tư vấn và indexing; nó không có quyền quyết định giao dịch như người dùng hay quản trị viên. Khách hàng và quản trị viên đi qua Backend để được xác thực và phân quyền.

### 84. Vì sao Frontend chỉ gọi Spring Boot? ★

Dạ, Spring Boot là cổng API công khai và là nơi kiểm tra danh tính, quyền truy cập và dữ liệu nghiệp vụ. Nếu trình duyệt gọi thẳng AI Service, Qdrant hoặc MySQL, hệ thống sẽ khó bảo vệ khóa nội bộ và khó bảo đảm dữ liệu hiện hành. Ranh giới này còn giúp đổi nhà cung cấp AI mà không đổi luồng giao diện.

### 85. Ba lớp lưu trữ trên slide có vai trò gì?

Dạ, MySQL là nguồn chuẩn cho dữ liệu giao dịch; Qdrant lưu chỉ mục vector dẫn xuất; Redis được dùng cho cache hoặc trạng thái ở những cấu hình phù hợp. Riêng checkpoint LangGraph của bản demo GCP hiện dùng SQLite trên filesystem tạm, nên không thể nói mọi trạng thái hội thoại trên GCP đều nằm trong Redis.

### 86. Sản phẩm nào được phép hiển thị sau khi Qdrant trả ứng viên?

Dạ, AI Service trả mã sản phẩm, điểm và thông tin kỹ thuật cần thiết. Backend dùng mã đó để lấy lại Product Card từ MySQL, kiểm tra trạng thái hiện hành và trả dữ liệu hiển thị. Một vector còn tồn tại trong Qdrant không đủ để khẳng định sản phẩm đang bán hoặc có hàng.

### 87. API `auto` khác gì ba API tìm kiếm riêng?

Dạ, `auto` chọn nhánh tìm kiếm theo đầu vào: văn bản, ảnh hoặc cả hai. Các API riêng phục vụ khi giao diện hay kiểm thử đã biết modality. Dù đi nhánh nào, kết quả vẫn phải được Backend xác minh trước khi hiển thị dữ liệu nghiệp vụ.

### 88. Nếu ảnh có nhiều vật thể, hệ thống tìm vật thể nào?

Dạ, detector có thể trả nhiều vùng; giao diện cho người dùng chọn hoặc điều chỉnh vùng quan tâm. Khi có crop do người dùng chọn, pipeline ưu tiên vùng đó để tạo embedding, nhờ vậy tránh tìm nhầm áo khi người dùng muốn tìm túi. Nếu không có vùng hợp lệ thì dùng ảnh đầy đủ, nhưng kết quả có thể kém tập trung hơn.

### 89. Vì sao search response chỉ trả mã sản phẩm thay vì toàn bộ entity?

Dạ, mã sản phẩm là hợp đồng liên kết giữa AI và Backend. AI không cần nhận toàn bộ JPA Entity hoặc quyền đọc MySQL; Backend chịu trách nhiệm lấy giá, tồn kho và thuộc tính hiện hành. Cách tách này giảm dữ liệu truyền qua AI và giữ quyết định nghiệp vụ ở đúng thành phần.

### 90. Checkout preview khác confirm như thế nào? ★

Dạ, preview tính giá, giảm giá và coupon dự kiến để người dùng xem. Confirm phải kiểm tra lại giỏ hàng, địa chỉ, sản phẩm, tồn kho và coupon trong transaction rồi mới tạo đơn. Giá hoặc số lượng tồn có thể thay đổi giữa hai bước, nên không thể dùng kết quả preview làm cam kết giao dịch.

### 91. Hệ thống quản lý vòng đời đơn COD ra sao?

Dạ, trạng thái chính đi từ PENDING sang CONFIRMED, SHIPPING rồi DELIVERED. Mỗi chuyển trạng thái phải kiểm tra trạng thái hiện tại, vai trò thực hiện và tác động lên tồn kho hoặc thanh toán; hủy đơn chỉ được phép ở trạng thái hợp lệ. Lịch sử trạng thái được lưu để truy vết.

### 92. Vì sao cần lưu snapshot đơn hàng?

Dạ, tên, giá hoặc khuyến mãi của sản phẩm có thể thay đổi sau khi khách đặt. Đơn hàng cần lưu thông tin tại thời điểm giao dịch để biên nhận và đối soát không đổi theo catalog hiện hành. Dữ liệu catalog mới phục vụ các lượt mua sau, không viết lại lịch sử đơn cũ.

### 93. Dự án có thanh toán online chưa? Vì sao báo cáo có bảng payment?

Dạ, luồng người dùng hiện tại đặt hàng COD; các bảng và logic payment phục vụ ghi nhận trạng thái thanh toán, đối soát và thiết kế vòng đời đơn. Có bảng `payment` không đồng nghĩa đã tích hợp cổng thanh toán trực tuyến. Tích hợp thanh toán thật và hoàn tiền tự động vẫn là hướng phát triển.

### 94. Vì sao catalog có màu White, Ecru, Ivory lại làm tìm kiếm sai?

Dạ, tên màu tiếng Anh và bản Việt hóa có thể dùng các từ gần nhau nhưng không đồng nhất. Nếu chuẩn hóa sai, bộ lọc có thể gán sản phẩm màu trắng thành màu kem hoặc ngược lại. Em dùng khóa màu chuẩn hóa và ưu tiên màu gốc của catalog khi có xung đột; các ca hồi quy kiểm tra ví dụ White, Ecru và Ivory.

### 95. Lỗi URL `master.m3u8` liên quan gì đến Image Search?

Dạ, đó là URL media dạng playlist video, không phải ảnh hợp lệ cho image embedding. Nếu đưa nhầm vào payload indexing, tác vụ tải và giải mã ảnh có thể lỗi hoặc thiếu vector ảnh. Mapper lọc/chuẩn hóa URL media trước khi đồng bộ, và báo cáo có 8/8 ca hồi quy URL ảnh đạt.

### 96. Vì sao health check SMTP không nên làm sập trạng thái toàn hệ thống?

Dạ, SMTP là dịch vụ phụ trợ. Nếu một lỗi gửi mail khiến liveness/readiness tổng thể thất bại, hệ thống có thể bị đánh dấu không phục vụ dù catalog, giỏ hàng và đơn hàng vẫn hoạt động. Em tách trạng thái mail khỏi tín hiệu sống của nghiệp vụ lõi, đồng thời vẫn theo dõi lỗi mail riêng.

### 97. Upload quá lớn và đăng nhập dồn dập được xử lý thế nào?

Dạ, request upload quá giới hạn trả HTTP 413; chuỗi yêu cầu xác thực vượt giới hạn trả 429 và có thông tin thử lại. Đây là các lớp bảo vệ đầu vào và tốc độ. Chúng hỗ trợ giảm lạm dụng, nhưng không thay thế kiểm thử an ninh toàn diện.

### 98. Correlation ID để làm gì? ★

Dạ, nó gắn cùng một mã theo request qua Backend và AI Service để đối chiếu lỗi, độ trễ và log. Khi AI trả kết quả bất thường, em có thể lần theo một request thay vì tìm theo thời điểm gần đúng. Mã này không nên chứa token hay dữ liệu cá nhân, và phải được tách giữa các request đồng thời.

### 99. Health, readiness và metrics khác nhau thế nào?

Dạ, health hoặc liveness cho biết tiến trình còn hoạt động; readiness cho biết thành phần có thể nhận loại request cụ thể hay chưa; metrics ghi nhận số lượt, độ trễ và lỗi để theo dõi theo thời gian. Một model ảnh chưa sẵn sàng không nhất thiết làm nghiệp vụ catalog hoặc Text Search thất bại. Vì vậy cần xem trạng thái theo capability, không chỉ một đèn xanh tổng quát.

### 100. Slide ghi 26 controller, 126 mapping và 14 endpoint. Chúng chứng minh điều gì?

Dạ, đó là thống kê bề mặt API ở thời điểm làm slide: Spring Boot có 26 controller và 126 request mapping; FastAPI được nhóm thành 14 endpoint cho search, assistant, indexing và vận hành. Số lượng API cho thấy phạm vi tích hợp nhưng không phải bằng chứng chất lượng. Chất lượng được đánh giá bằng test nghiệp vụ, contract, E2E và các gate.

### 101. P95 từ 693,46 xuống 182,79 ms nhờ đâu? ★

Dạ, slide ghi ba thay đổi chính: cache catalog, loại bỏ lần đọc giỏ hàng dư và thêm chỉ mục cho truy vấn giá mới nhất. Trong bài tải hỗn hợp catalog–cart, P95 giảm khoảng 73,6%, còn 182,79 ms. Đây là so sánh trên cùng loại workload được báo cáo; không suy ra mọi endpoint đều nhanh hơn 73,6%.

### 102. Vì sao P95 bài soak 48,863 ms thấp hơn P95 bài tải hỗn hợp 182,79 ms?

Dạ, hai bài đo có thao tác, tỷ lệ trộn request, số worker và thời gian khác nhau. Bài soak gồm các thao tác checkout/payment/order theo kịch bản riêng; bài tải hỗn hợp tập trung catalog–cart. Không nên so trực tiếp hai P95 để kết luận checkout luôn nhanh hơn catalog; mỗi số chỉ có ý nghĩa cùng workload của nó.

### 103. 19,999 request/giây trong slide khác 8 request/giây ở bài soak thế nào?

Dạ, 19,999 request/giây thuộc bài tải hỗn hợp 6.050 request trong khoảng 301 giây. Trung bình tám request/giây thuộc bài soak 57.600 request trong hai giờ. Đây là hai workload khác nhau, không phải hai kết quả mâu thuẫn của cùng phép đo.

### 104. Assistant P95 đạt 2,776 giây nhưng P99 gần 9,7 giây: có đáng lo không? ★

Dạ, có. P95 đạt gate AI không quá 5 giây trong bài tải đã chạy, nhưng P99 và thời gian cực đại lần lượt khoảng 9,704 và 9,751 giây. Điều đó cho thấy một số request vẫn chậm rõ rệt. Trước khi vận hành thật cần thử dài hơn, tải phân tán và theo dõi đuôi trễ, đặc biệt ở các phiên hội thoại dài.

### 105. Vì sao P95 Hybrid ở bảng ablation là 2,105 giây nhưng bài tải AI là 0,516 giây?

Dạ, đó là hai phép đo khác nhau về tập truy vấn, workload và cách chạy. Số 2,105 giây thuộc đánh giá chất lượng/cấu hình Hybrid; 0,516 giây là P95 lớn nhất trong ba vòng tải AI đại diện ghi ở báo cáo. Chỉ so sánh độ trễ giữa các cấu hình khi điều kiện đo giống nhau.

### 106. P95 thấp có chứng minh hỗ trợ dưới 50 người dùng đồng thời không?

Dạ, chưa. Slide nêu mức người dùng mục tiêu, nhưng bài tải Backend có 10 worker và bài tải AI dùng hai worker; bản GCP demo còn giới hạn tối đa một AI instance với concurrency một. Vì vậy em chỉ kết luận đạt các gate trên workload đã chạy. Cần mô phỏng số phiên và hành vi người dùng tương ứng để xác minh mục tiêu đồng thời.

### 107. Nếu hội đồng hỏi “vì sao chọn mô hình này thay vì mô hình khác”, trả lời thế nào?

Dạ, em nêu tiêu chí trước: chất lượng trên bộ truy vấn, độ trễ, chi phí, khả năng triển khai và tích hợp. Em trình bày vai trò của từng mô hình: YOLO phát hiện vùng, embedding tạo vector, LLM hiểu ý định và diễn đạt; các lựa chọn local và GCP cũng khác nhau do hạ tầng. Em không khẳng định mô hình được chọn tốt nhất tuyệt đối khi chưa benchmark rộng trên cùng điều kiện.

### 108. Khi hội đồng chỉ ra slide nói “fusion và rerank” nhưng cấu hình vận hành lại tắt rerank, có mâu thuẫn không? ★

Dạ, slide use case và pipeline liệt kê các năng lực hoặc bước tùy chọn của AI Service, còn bảng ablation xác định cấu hình được dùng khi nghiệm thu. Cấu hình Hybrid cuối là image-conditioned và tắt rerank vì phù hợp ràng buộc hơn trong bộ thử; fusion và rerank vẫn là phương án đối chứng/adapter. Em sẽ mở phụ lục kết quả để phân biệt thiết kế tổng quát với cấu hình đang chạy.

### 109. Nếu hội đồng yêu cầu chứng minh live, em nên mở bằng chứng nào?

Dạ, em bắt đầu bằng luồng demo: tìm bằng text, tìm bằng ảnh, thêm ràng buộc trong Hybrid, hỏi tiếp qua trợ lý rồi đi đến sản phẩm và đặt COD. Sau đó mở phụ lục slide theo câu hỏi: A1/A7/A8 cho ground truth và metric, A2 cho hiệu năng, A3 cho API, A4 cho lỗi đã sửa, A5 cho YOLO, A9 cho tích hợp và NFR. Demo thể hiện hành vi; artifact kiểm thử mới chứng minh phạm vi nghiệm thu.

### 110. Nếu kết quả demo khác số trong báo cáo thì trả lời sao?

Dạ, em kiểm tra trước môi trường, snapshot, model, collection, cấu hình rerank và trạng thái dịch vụ. Metric trong báo cáo gắn với bộ dữ liệu và cấu hình cố định; một truy vấn demo mới hoặc bản GCP khác model không thể lấy làm phép lặp trực tiếp. Nếu có lỗi thật, em ghi nhận và chỉ rõ phần nào của kết luận vẫn được artifact hỗ trợ, không giải thích bằng cách đổi nghĩa chỉ số.

## Các con số cần nhớ

| Nội dung | Kết quả trong báo cáo | Giới hạn cần nói kèm |
|---|---|---|
| Catalog | 1.000 sản phẩm | Lĩnh vực thời trang |
| Text Search | Hit@5 1,000; NDCG@5 0,941 | Hit trên 90 truy vấn dương; 10 truy vấn âm đánh giá riêng |
| BM25 | Hit@5 0,756; NDCG@5 0,689 | Cùng 90 truy vấn dương |
| Ảnh catalog | Exact Hit@1 0,980; Exact Hit@5 1,000; NDCG@5 0,853 | 100 ảnh |
| Ảnh bên ngoài | Exact Hit@1 0,930; Exact Hit@5 0,970; NDCG@5 0,810 | 100 ảnh paired |
| Hybrid được chọn | Strict Hit@5 0,980; NDCG@5 0,873; NDCG theo yêu cầu 0,958; ràng buộc 0,990 | 100 truy vấn; image-conditioned, rerank tắt |
| RAG + memory | Grounding 1,000; Context Precision 0,946; Context Recall 0,944; critical 12/12 | Theo scorer và tập đánh giá; chưa chứng minh luôn đúng |
| Hội thoại dài | 10 phiên, tổng 230 request đạt | Các phiên đã kiểm thử |
| YOLO | Precision 0,875; Recall 0,760; mAP50 0,849; mAP50–95 0,685 | Chất lượng detector |
| Backend / E2E | 102/102 ca; 5/5 hành trình | Các ca đã xây dựng |
| Soak | 57.600/57.600 request trong hai giờ | Workload cụ thể; trung bình 8 request/giây |
| Tải hỗn hợp Backend | 6.050/6.050 request; 19,999 request/giây; P95 182,79 ms | 10 worker, khoảng 301 giây, catalog–cart |
| Tải Assistant | P95 2,776 giây; P99 9,704 giây | 72 request với hai worker; đuôi trễ vẫn còn |
| Tương thích | Firefox/WebKit 8/8; NFR-06 đạt một phần | Chưa có đủ artifact Chrome/Edge hoặc Safari trên thiết bị thật |

## Cách luyện trả lời

1. Học trước các câu có dấu ★, đặc biệt 1, 4, 5, 26, 29, 35, 43, 46, 51, 57, 60, 69, 73, 77, 81, 90, 101, 104 và 108.
2. Mỗi câu trả lời theo thứ tự: kết luận trực tiếp → cơ chế hoặc bằng chứng → giới hạn liên quan.
3. Khi được hỏi số liệu, luôn nêu tập truy vấn và cấu hình. Phân biệt kết quả benchmark với smoke test triển khai.
4. Nếu chưa đo: “Dạ, phần đó em chưa có thực nghiệm để kết luận. Hiện em đã kiểm tra …; để xác minh thêm cần …”.
5. Nếu không nhớ chi tiết: “Dạ, em xin mở bảng kết quả/mã nguồn tương ứng để trả lời chính xác”.
6. Chuẩn bị demo: tìm bằng ảnh, bổ sung yêu cầu văn bản, hội thoại đổi điều kiện, xem sản phẩm và đặt COD. Chuẩn bị video dự phòng khi mạng hoặc provider gặp lỗi.

## Những phát biểu cần tránh và cách nói chính xác

| Phát biểu dễ bị phản biện | Cách nói chính xác |
|---|---|
| “Độ chính xác hệ thống là 100%.” | “Text Hit@5 đạt 1,000 trên 90 truy vấn dương.” |
| “RAG loại bỏ hoàn toàn hallucination.” | “RAG giảm rủi ro; grounding đạt 1,000 trong bộ kiểm thử hiện có.” |
| “YOLO nhận diện đúng sản phẩm.” | “YOLO phát hiện vùng và nhóm vật thể; embedding truy hồi sản phẩm.” |
| “Hybrid cộng điểm text và ảnh.” | “Cấu hình được chọn là image-conditioned; fusion là một đối chứng.” |
| “GCP đạt nguyên các metric local.” | “GCP có cấu hình embedding khác; cần benchmark lại để so sánh.” |
| “Memory trên GCP luôn tồn tại.” | “Checkpoint demo trên filesystem tạm có thể mất khi instance dừng.” |
| “57.600 request là 57.600 người dùng đồng thời.” | “Đó là tổng request của bài soak hai giờ theo workload đã định nghĩa.” |
| “Hệ thống đã sẵn sàng thương mại.” | “Đạt nghiệm thu nội bộ và triển khai thử nghiệm trong phạm vi đồ án.” |
| “Reviewer có kappa 1 là đánh giá độc lập đã hoàn tất.” | “Phải kiểm tra trạng thái human review; AI pre-score không thay thế reviewer con người.” |

## Nguồn và lưu ý đối chiếu

- `report-datn/Sections/04-CongNgheVaQuyetDinhLuaChon.tex`: lựa chọn công nghệ và vai trò từng thành phần.
- `report-datn/Sections/05-ThietKeHeThong.tex`: kiến trúc, hợp đồng, đồng bộ và kiểm soát nghiệp vụ.
- `report-datn/Sections/06-HienThucVaTrienKhaiHeThong.tex`: dữ liệu Zara, fine-tune YOLO và bản GCP thực tế.
- `report-datn/Sections/07-KiemThuHeThong.tex`: ground truth, baseline, ablation và kết quả nghiệm thu.
- `report-datn/Sections/08-KetLuanVaHuongPhatTrien.tex`: kết luận, hạn chế và hướng phát triển.
- `evals/search_evaluation/text/semantic_challenge/reports/compare_keyword_vs_vector_v4_reduced_no_rerank.md`: so sánh BM25–vector.
- `evals/search_evaluation/hybrid/reports/hybrid_ablation_five_way_gt_v4_20260911.md`: so sánh hybrid và bootstrap.
- `presentation/Presentation.pptx`: các slide chính và phụ lục A1–A9, đặc biệt mục tiêu, API, lỗi đã sửa và kết quả hiệu năng.
- `report-datn/HK253-DATN-071_2210352.pdf`: bản báo cáo PDF được chỉ định; nội dung được đối chiếu qua các tệp LaTeX của cùng báo cáo do công cụ trích xuất PDF tại môi trường này không hoạt động.
- `service-ai/` và `service-api-ecommerce/`: mã nguồn, cấu hình và test để đối chiếu một số hành vi cụ thể như bộ lọc màu, URL ảnh, rate limit và xử lý lỗi.

Một số tài liệu trung gian còn mô tả fusion, cấu hình memory dự kiến hoặc trạng thái baseline pending. Bộ câu hỏi ưu tiên bảng tổng hợp trong báo cáo và mô tả triển khai cụ thể, đồng thời nêu giới hạn. Trước ngày bảo vệ, kiểm tra slide/PDF được chốt có khớp các số liệu và cấu hình này. Không dùng các điểm AI pre-score hoặc đồng thuận reviewer chưa xác nhận để tuyên bố đã đánh giá độc lập.
