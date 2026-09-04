# Kế hoạch kiểm thử các thành phần ngoài AI Service

## 1. Mục đích

Kế hoạch này xác định phạm vi, phương pháp, dữ liệu, môi trường và tiêu chí đánh giá cho các thành phần của hệ thống nằm ngoài AI Service. Mục tiêu là kiểm chứng rằng các luồng nghiệp vụ hoạt động đúng, dữ liệu được lưu trữ nhất quán, các thành phần tích hợp đúng hợp đồng và hệ thống có khả năng xử lý an toàn khi AI Service hoặc một dịch vụ phụ thuộc gặp lỗi.

Kết quả kiểm thử được dùng làm minh chứng cho phần đánh giá hệ thống, đồng thời tạo cơ sở để hồi quy khi hệ thống được thay đổi.

## 2. Phạm vi

### 2.1. Trong phạm vi

- Giao diện người dùng trên các thiết bị và trình duyệt được hỗ trợ.
- API nghiệp vụ và các quy tắc kiểm tra dữ liệu đầu vào.
- Xác thực, phân quyền và quản lý phiên đăng nhập.
- Các luồng tạo, đọc, cập nhật, xóa dữ liệu theo chức năng của hệ thống.
- Cơ sở dữ liệu, tính toàn vẹn dữ liệu và cơ chế migration/khôi phục.
- Lưu trữ tệp, tải lên, tải xuống và kiểm soát loại/kích thước tệp, nếu hệ thống có chức năng này.
- Các hàng đợi, tác vụ nền, thông báo hoặc dịch vụ ngoài khác, nếu có.
- Hợp đồng tích hợp giữa hệ thống và AI Service: định dạng yêu cầu/phản hồi, xác thực, timeout, retry, trạng thái lỗi và khả năng suy giảm có kiểm soát.
- Các thuộc tính phi chức năng của phần ngoài AI Service: hiệu năng, bảo mật, khả dụng, tương thích và khả năng quan sát.

### 2.2. Ngoài phạm vi

- Độ chính xác, độ phù hợp hoặc chất lượng nội dung do mô hình AI sinh ra.
- Quá trình huấn luyện, tinh chỉnh, lựa chọn mô hình và đánh giá bộ dữ liệu AI.
- Hiệu năng suy luận bên trong AI Service, trừ thời gian chờ và cách hệ thống gọi xử lý kết quả của dịch vụ này.

> Ranh giới kiểm thử: AI Service được xem là một phụ thuộc bên ngoài và được thay bằng mock/stub trong phần lớn kiểm thử tự động. Một số kiểm thử tích hợp trên môi trường staging sử dụng AI Service thật để xác nhận hợp đồng đầu-cuối, nhưng không chấm chất lượng câu trả lời AI.

## 3. Mục tiêu chất lượng

Hệ thống đạt yêu cầu khi:

1. Các luồng nghiệp vụ chính và quy tắc phân quyền cho kết quả đúng với đặc tả.
2. Không xảy ra mất dữ liệu, tạo dữ liệu trùng ngoài ý muốn hoặc chuyển trạng thái không hợp lệ.
3. Lỗi từ AI Service và các dịch vụ phụ thuộc không làm treo ứng dụng hoặc lộ thông tin nội bộ.
4. API duy trì hợp đồng đã công bố và trả mã lỗi nhất quán.
5. Các luồng quan trọng đáp ứng ngưỡng hiệu năng đã xác định trong môi trường kiểm thử.
6. Không còn lỗi nghiêm trọng hoặc lỗ hổng mức cao trước khi nghiệm thu.

## 4. Chiến lược kiểm thử

Áp dụng mô hình tháp kiểm thử để phản hồi nhanh nhưng vẫn bao phủ luồng thực tế:

| Tầng kiểm thử | Đối tượng | Phụ thuộc AI Service | Thời điểm chạy |
|---|---|---|---|
| Unit test | Hàm xử lý, validator, service nghiệp vụ, kiểm tra quyền | Mock hoàn toàn | Mỗi commit/pull request |
| Component/API test | Endpoint, repository, database test, tác vụ nền | Stub theo các kịch bản định trước | Mỗi pull request |
| Contract test | Schema yêu cầu/phản hồi giữa backend và AI Service/dịch vụ ngoài | Mock server và một lượt xác nhận với dịch vụ thật | Mỗi thay đổi hợp đồng và trước phát hành |
| Integration test | Backend, database, cache, lưu trữ, hàng đợi | Stub mặc định; dịch vụ thật trên staging cho smoke test | Hằng ngày hoặc trước khi merge |
| End-to-end test | Luồng người dùng trên giao diện đến dữ liệu | Stub ổn định; một nhóm smoke test dùng AI Service thật | Trước phát hành |
| Phi chức năng | Hiệu năng, bảo mật, phục hồi, tương thích | Có thể dùng stub để cô lập tải | Theo mốc kiểm thử |

Ưu tiên tự động hóa các unit test, API test và luồng end-to-end quan trọng. Kiểm thử khám phá được thực hiện cho giao diện, thông báo lỗi và các tình huống khó mô hình hóa tự động.

## 5. Môi trường và dữ liệu kiểm thử

### 5.1. Môi trường

- **Local/CI:** chạy unit test, lint, kiểm tra schema và component test bằng database/dịch vụ tạm thời.
- **Staging:** cấu hình gần giống production, tách biệt dữ liệu thật; chạy integration, end-to-end, hiệu năng và smoke test với AI Service thật.
- **Production:** chỉ chạy smoke test không phá hủy dữ liệu sau triển khai; không thực hiện kiểm thử tải nếu chưa có phê duyệt.

Mỗi bản chạy phải ghi nhận mã phiên bản ứng dụng, phiên bản database migration, cấu hình môi trường và phiên bản hợp đồng API.

### 5.2. Dữ liệu

- Dùng dữ liệu giả lập, không dùng thông tin cá nhân hoặc bí mật thật.
- Chuẩn bị tài khoản cho từng vai trò: chưa đăng nhập, người dùng thông thường, người sở hữu tài nguyên và quản trị viên (điều chỉnh theo vai trò thực tế của hệ thống).
- Bao phủ dữ liệu hợp lệ, thiếu trường, sai kiểu, giá trị biên, Unicode/tiếng Việt, dữ liệu trùng, tệp quá dung lượng và nội dung có khả năng gây injection.
- Dữ liệu test phải có thể tạo lại bằng seed/fixture; mỗi test tự dọn dữ liệu hoặc chạy trong transaction cô lập.
- Khóa API và secret dùng trong CI/staging được lấy từ secret manager hoặc biến môi trường, không ghi vào mã nguồn hay log.

## 6. Ma trận kiểm thử đề xuất

### 6.1. Xác thực và phân quyền

| Mã | Kịch bản | Kết quả mong đợi | Mức ưu tiên |
|---|---|---|---|
| AUTH-01 | Đăng nhập bằng thông tin hợp lệ | Tạo phiên/token hợp lệ và chuyển đúng màn hình | P0 |
| AUTH-02 | Sai mật khẩu, tài khoản không tồn tại hoặc dữ liệu thiếu | Từ chối với thông báo an toàn, không tiết lộ tài khoản có tồn tại hay không | P0 |
| AUTH-03 | Token hết hạn, sai chữ ký hoặc bị thu hồi | Trả 401; không cho truy cập dữ liệu | P0 |
| AUTH-04 | Người dùng gọi chức năng ngoài quyền | Trả 403 và không thay đổi dữ liệu | P0 |
| AUTH-05 | Người dùng truy cập tài nguyên của người khác bằng cách đổi ID | Từ chối truy cập; không lộ nội dung tài nguyên | P0 |
| AUTH-06 | Đăng xuất rồi dùng lại phiên/token | Phiên không còn hiệu lực theo thiết kế | P1 |
| AUTH-07 | Gửi nhiều lần yêu cầu đăng nhập thất bại | Rate limit/khóa tạm thời hoạt động theo cấu hình | P1 |

### 6.2. API và nghiệp vụ

Áp dụng nhóm ca sau cho từng chức năng nghiệp vụ được mô tả trong đặc tả/use case:

| Mã | Kịch bản | Kết quả mong đợi | Mức ưu tiên |
|---|---|---|---|
| API-01 | Gửi yêu cầu hợp lệ cho luồng chính | Mã trạng thái, nội dung phản hồi và dữ liệu lưu đúng | P0 |
| API-02 | Thiếu trường bắt buộc hoặc sai kiểu dữ liệu | Trả 400/422 với mã lỗi có cấu trúc; không ghi dữ liệu dở dang | P0 |
| API-03 | Giá trị đúng tại, dưới và trên biên | Xử lý đúng quy tắc validation | P1 |
| API-04 | ID không tồn tại hoặc sai định dạng | Trả 404 hoặc 400 nhất quán | P1 |
| API-05 | Gửi lặp một yêu cầu tạo/cập nhật | Không tạo bản ghi trùng nếu thao tác yêu cầu tính idempotent | P1 |
| API-06 | Hai người dùng cập nhật đồng thời | Không mất cập nhật; áp dụng đúng quy tắc khóa/version | P1 |
| API-07 | Phân trang, lọc và sắp xếp | Kết quả đúng, ổn định, không trùng/thiếu giữa các trang | P1 |
| API-08 | Chuỗi Unicode, dấu tiếng Việt và ký tự đặc biệt | Lưu, tìm kiếm và hiển thị không lỗi mã hóa | P1 |
| API-09 | Lỗi bất ngờ từ tầng dữ liệu | Rollback transaction; trả lỗi chung có correlation ID; không lộ stack trace | P0 |

Với mỗi use case chính, lập ít nhất một ca thành công, một ca validation thất bại, một ca không đủ quyền và một ca phụ thuộc gặp lỗi.

### 6.3. Dữ liệu và lưu trữ

| Mã | Kịch bản | Kết quả mong đợi | Mức ưu tiên |
|---|---|---|---|
| DATA-01 | Tạo/cập nhật/xóa dữ liệu qua API | Dữ liệu và các quan hệ được lưu nhất quán | P0 |
| DATA-02 | Thao tác thất bại giữa transaction | Toàn bộ thay đổi được rollback | P0 |
| DATA-03 | Xóa bản ghi đang được tham chiếu | Tuân thủ đúng quy tắc chặn, cascade hoặc soft delete | P1 |
| DATA-04 | Chạy migration trên bản sao dữ liệu staging | Migration thành công, ứng dụng đọc/ghi bình thường | P0 |
| DATA-05 | Khôi phục từ bản sao lưu | Khôi phục được dữ liệu và xác nhận tính toàn vẹn | P1 |
| FILE-01 | Tải lên loại và kích thước tệp hợp lệ | Lưu thành công, metadata đúng, chỉ người có quyền truy cập | P1 |
| FILE-02 | Tệp sai loại, quá dung lượng hoặc tên tệp nguy hiểm | Bị từ chối và không để lại tệp rác | P0 |
| FILE-03 | Dịch vụ lưu trữ gián đoạn | Trả lỗi có kiểm soát; dữ liệu không ở trạng thái nửa hoàn tất | P1 |

Các ca `FILE-*` chỉ áp dụng nếu hệ thống có chức năng lưu trữ tệp.

### 6.4. Giao diện người dùng

| Mã | Kịch bản | Kết quả mong đợi | Mức ưu tiên |
|---|---|---|---|
| UI-01 | Thực hiện từng luồng người dùng chính | Hoàn tất được luồng và dữ liệu hiển thị đúng | P0 |
| UI-02 | Nhập dữ liệu không hợp lệ | Hiển thị lỗi gần trường nhập; giữ lại dữ liệu hợp lệ đã nhập | P1 |
| UI-03 | Gửi biểu mẫu nhiều lần/nhấn nút liên tục | Không tạo thao tác trùng; có trạng thái đang xử lý | P1 |
| UI-04 | API trả 401/403/404/422/500 | Hiển thị trạng thái phù hợp, không lộ chi tiết kỹ thuật | P0 |
| UI-05 | Mạng chậm, mất mạng hoặc yêu cầu timeout | Không treo vô hạn; cho phép thử lại an toàn | P0 |
| UI-06 | Màn hình ở kích thước desktop và mobile mục tiêu | Không che khuất chức năng chính, không tràn nội dung | P1 |
| UI-07 | Điều hướng bằng bàn phím và nhãn trường | Luồng chính sử dụng được; focus hiển thị rõ | P2 |
| UI-08 | Tải lại trang hoặc dùng nút Back/Forward | Trạng thái và điều hướng nhất quán | P1 |

### 6.5. Tích hợp với AI Service

Nhóm này chỉ đánh giá khả năng tích hợp, không đánh giá nội dung AI:

| Mã | Phản hồi của AI Service | Kết quả mong đợi của hệ thống ngoài AI Service | Mức ưu tiên |
|---|---|---|---|
| AI-INT-01 | 2xx, response đúng schema | Parse và chuyển trạng thái nghiệp vụ đúng; lưu đúng trường cần thiết | P0 |
| AI-INT-02 | 2xx nhưng thiếu trường/sai kiểu | Không làm hỏng dữ liệu; ghi log có correlation ID; báo lỗi có kiểm soát | P0 |
| AI-INT-03 | 400/401/403 | Không retry vô hạn; ánh xạ lỗi phù hợp và không lộ secret | P0 |
| AI-INT-04 | 429 hoặc 5xx tạm thời | Retry có giới hạn/backoff theo thiết kế; không tạo tác vụ trùng | P0 |
| AI-INT-05 | Timeout hoặc mất kết nối | Hủy/chuyển trạng thái thất bại hoặc chờ xử lý đúng thiết kế; UI không treo | P0 |
| AI-INT-06 | Phản hồi chậm nhưng còn trong timeout | Hiển thị trạng thái đang xử lý và nhận kết quả một lần | P1 |
| AI-INT-07 | Gửi lại callback/webhook trùng, nếu có | Xử lý idempotent; không nhân đôi kết quả | P1 |
| AI-INT-08 | Payload gần/vượt giới hạn cho phép | Chặn trước khi gọi hoặc xử lý lỗi rõ ràng | P1 |
| AI-INT-09 | AI Service ngừng hoạt động kéo dài | Chức năng không phụ thuộc AI vẫn dùng được; có cảnh báo/giám sát | P0 |
| AI-INT-10 | Thay đổi schema không tương thích | Contract test thất bại trước khi triển khai | P0 |

Stub AI Service cần hỗ trợ cấu hình độ trễ, mã HTTP, response sai schema, ngắt kết nối và số lần thất bại trước khi thành công.

### 6.6. Tác vụ nền, hàng đợi và thông báo

Chỉ áp dụng nếu kiến trúc có các thành phần tương ứng:

- Tác vụ được xử lý đúng một lần về mặt nghiệp vụ dù worker nhận lại message.
- Message lỗi được retry có giới hạn và chuyển vào dead-letter queue hoặc trạng thái thất bại để xử lý.
- Worker khởi động lại không làm mất tác vụ đang chờ.
- Thứ tự xử lý được bảo đảm ở nơi nghiệp vụ yêu cầu.
- Thông báo không gửi trùng; nội dung không chứa dữ liệu nhạy cảm ngoài phạm vi người nhận.
- Lỗi dịch vụ email/push không rollback nghiệp vụ chính nếu thiết kế không yêu cầu.

## 7. Kiểm thử phi chức năng

### 7.1. Hiệu năng và độ ổn định

Trước khi chạy cần chốt ngưỡng dựa trên yêu cầu hệ thống. Nếu báo cáo chưa quy định, dùng các ngưỡng khởi đầu sau và điều chỉnh sau lần đo baseline:

- API không gọi AI: p95 không quá 500 ms và tỷ lệ lỗi dưới 1% ở tải dự kiến.
- API gọi AI: đo riêng thời gian xử lý của hệ thống ngoài AI Service; timeout tổng phải hữu hạn và đúng cấu hình.
- Luồng đọc phổ biến: kiểm tra tải bằng 1x tải dự kiến trong 15 phút.
- Luồng hỗn hợp đọc/ghi: kiểm tra tải bằng 1x tải dự kiến trong 30 phút.
- Spike test: tăng từ 1x lên 2x tải dự kiến trong thời gian ngắn; hệ thống không mất dữ liệu và phục hồi sau khi tải giảm.
- Soak test: chạy 2--4 giờ để phát hiện rò rỉ kết nối, bộ nhớ và backlog hàng đợi.

Thu thập p50/p95/p99, throughput, tỷ lệ lỗi, CPU, bộ nhớ, số kết nối database, độ trễ truy vấn và độ dài hàng đợi. Kịch bản tải AI nên dùng stub có độ trễ cố định để tách hiệu năng hệ thống khỏi biến động mô hình.

### 7.2. Bảo mật

- Kiểm tra xác thực/phân quyền ở cả UI và API; API là lớp quyết định cuối cùng.
- Kiểm tra IDOR, SQL/NoSQL injection, XSS, CSRF (nếu dùng cookie), path traversal và tải tệp nguy hiểm.
- Kiểm tra rate limiting cho đăng nhập, API tốn tài nguyên và endpoint gọi AI.
- Bảo đảm secret/token không xuất hiện trong response, log, mã nguồn hoặc bundle phía client.
- Kiểm tra cookie/token có cấu hình thời hạn và thuộc tính bảo vệ phù hợp.
- Quét dependency và image container; xử lý lỗ hổng mức Critical/High trước nghiệm thu hoặc có biên bản chấp nhận rủi ro.
- Log sự kiện nhạy cảm phải đủ để truy vết nhưng không chứa mật khẩu, token hay dữ liệu cá nhân không cần thiết.

### 7.3. Khả năng phục hồi và quan sát

- Mô phỏng database, cache, lưu trữ, hàng đợi và AI Service tạm thời không khả dụng.
- Xác nhận timeout, retry và circuit breaker (nếu có) không khuếch đại sự cố.
- Mỗi request quan trọng có correlation/request ID xuyên suốt các thành phần.
- Log có cấu trúc và phân biệt được lỗi người dùng, lỗi nghiệp vụ và lỗi hệ thống.
- Metric/alert phát hiện tỷ lệ lỗi, độ trễ, hàng đợi tồn và số lần gọi AI thất bại vượt ngưỡng.
- Thực hiện một lần diễn tập backup/restore và ghi nhận RPO/RTO thực tế.

### 7.4. Tương thích

- Kiểm thử trên hai trình duyệt chính mà nhóm dự án cam kết hỗ trợ; ưu tiên Chromium và Firefox/Safari tùy đối tượng người dùng.
- Kiểm tra kích thước màn hình desktop và mobile mục tiêu.
- Kiểm tra múi giờ, định dạng ngày giờ và tiếng Việt có dấu xuyên suốt UI, API và database.

## 8. Truy vết yêu cầu và mức ưu tiên

Tạo ma trận truy vết theo mẫu sau để bảo đảm mọi yêu cầu ngoài AI Service đều có minh chứng:

| Yêu cầu/Use case | Test case | Tầng test | Tự động/Thủ công | Trạng thái | Minh chứng |
|---|---|---|---|---|---|
| UC-xx | TC-xx-01 | API/E2E | Tự động | Pass/Fail/Blocked | Link report/log/ảnh |

Quy ước ưu tiên:

- **P0:** luồng cốt lõi, xác thực/phân quyền, toàn vẹn dữ liệu, lỗi làm hệ thống không sử dụng được.
- **P1:** chức năng quan trọng hoặc tình huống biên có khả năng xảy ra.
- **P2:** cải thiện trải nghiệm, tương thích ít gặp hoặc rủi ro thấp.

## 9. Điều kiện bắt đầu, tạm dừng và hoàn tất

### 9.1. Điều kiện bắt đầu

- Yêu cầu/use case và tiêu chí chấp nhận đã được xác định.
- Bản build triển khai thành công trên môi trường kiểm thử.
- Database migration, seed data, tài khoản theo vai trò và stub AI Service sẵn sàng.
- API schema và phiên bản các dịch vụ phụ thuộc đã được ghi nhận.

### 9.2. Điều kiện tạm dừng

- Môi trường không ổn định khiến kết quả không thể tái hiện.
- Lỗi P0 chặn phần lớn test case liên quan.
- Dữ liệu hoặc phiên bản dịch vụ không đúng với bản build đang kiểm thử.

Sau khi khắc phục, chạy lại ca lỗi, các ca liên quan và smoke test trước khi tiếp tục.

### 9.3. Tiêu chí hoàn tất

- 100% test case P0 và ít nhất 95% test case P1 đã được thực thi.
- 100% test case P0 đạt; không còn lỗi Critical/High đang mở.
- Tỷ lệ đạt toàn bộ test case tối thiểu 95%; ca chưa đạt còn lại có đánh giá rủi ro và kế hoạch xử lý.
- Contract test giữa backend và AI Service đạt.
- Các luồng end-to-end chính đạt trên staging.
- Ngưỡng hiệu năng được đáp ứng và không phát hiện mất/tổn hại dữ liệu.
- Báo cáo kiểm thử, log, ảnh chụp và ma trận truy vết đã được lưu làm minh chứng.

## 10. Quy trình quản lý lỗi

Mỗi lỗi cần có: mã lỗi, phiên bản/môi trường, bước tái hiện, dữ liệu đầu vào đã ẩn thông tin nhạy cảm, kết quả thực tế, kết quả mong đợi, log/correlation ID và minh chứng.

| Mức độ | Diễn giải | Ví dụ |
|---|---|---|
| Critical | Mất dữ liệu, lộ dữ liệu/secret, vượt quyền nghiêm trọng hoặc hệ thống ngừng hoạt động | Người dùng đọc dữ liệu của người khác |
| High | Luồng cốt lõi không thể hoàn tất và không có cách vòng hợp lý | Không đăng nhập hoặc không lưu được nghiệp vụ chính |
| Medium | Chức năng phụ sai hoặc có cách vòng | Bộ lọc sai trong một trường hợp biên |
| Low | Lỗi giao diện/nội dung ít ảnh hưởng | Căn chỉnh hoặc thông báo chưa rõ |

Lỗi sau khi sửa phải được retest trên đúng phiên bản và chạy hồi quy vùng chức năng bị ảnh hưởng.

## 11. Lịch thực hiện đề xuất

| Giai đoạn | Công việc chính | Đầu ra |
|---|---|---|
| 1. Chuẩn bị | Chốt phạm vi, ánh xạ use case, tạo dữ liệu và stub AI | Danh sách test case, môi trường sẵn sàng |
| 2. Kiểm thử thành phần | Unit, API, database và contract test | Báo cáo tự động, độ bao phủ |
| 3. Kiểm thử tích hợp | Database, lưu trữ, tác vụ nền, AI boundary | Báo cáo tích hợp và danh sách lỗi |
| 4. Kiểm thử hệ thống | End-to-end, khám phá, tương thích | Ma trận truy vết và minh chứng |
| 5. Phi chức năng | Hiệu năng, bảo mật, phục hồi | Báo cáo chỉ số và rủi ro |
| 6. Hồi quy/nghiệm thu | Sửa lỗi, retest, smoke test bản phát hành | Báo cáo tổng kết và khuyến nghị phát hành |

Có thể triển khai trong 2--3 tuần tùy số lượng use case. Unit/API test được bổ sung song song với phát triển; kiểm thử hệ thống và phi chức năng thực hiện khi bản staging ổn định.

## 12. Đầu ra cần lưu cho báo cáo đồ án

- Danh sách test case và ma trận truy vết yêu cầu.
- Kết quả unit/API/E2E theo từng bản build.
- Bảng tổng hợp số ca Pass/Fail/Blocked theo nhóm chức năng và mức ưu tiên.
- Độ bao phủ mã nguồn ở các module nghiệp vụ quan trọng (không dùng một con số coverage duy nhất để thay cho chất lượng test).
- Biểu đồ p95, throughput và tỷ lệ lỗi của bài kiểm thử tải.
- Kết quả quét bảo mật/dependency và trạng thái xử lý phát hiện.
- Minh chứng các kịch bản AI Service timeout, 5xx, sai schema và phục hồi.
- Danh sách lỗi, mức độ, trạng thái và rủi ro còn lại.
- Kết luận mức đáp ứng tiêu chí hoàn tất và khuyến nghị phát hành.

## 13. Bảng tổng hợp kết quả mẫu

| Nhóm | Tổng số | Pass | Fail | Blocked | Tỷ lệ đạt | Lỗi Critical/High |
|---|---:|---:|---:|---:|---:|---:|
| Xác thực và phân quyền |  |  |  |  |  |  |
| API và nghiệp vụ |  |  |  |  |  |  |
| Dữ liệu và lưu trữ |  |  |  |  |  |  |
| Giao diện |  |  |  |  |  |  |
| Tích hợp AI Service |  |  |  |  |  |  |
| Phi chức năng |  |  |  |  |  |  |
| **Tổng** |  |  |  |  |  |  |

## 14. Việc cần chốt trước khi thực thi

1. Thay các nhóm thành phần tổng quát bằng đúng tên module/service trong thiết kế hệ thống.
2. Ánh xạ toàn bộ use case ở chương phân tích sang test case cụ thể.
3. Chốt vai trò người dùng, trình duyệt, thiết bị và tải dự kiến.
4. Chốt ngưỡng timeout/retry, p95, tỷ lệ lỗi, RPO và RTO.
5. Chọn công cụ test phù hợp với công nghệ đang dùng và tích hợp vào CI.
6. Xác định người thực hiện, người duyệt kết quả và nơi lưu minh chứng.
