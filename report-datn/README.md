# HCMUT Software Engineering Report Template

Template LaTeX cho báo cáo đồ án Công nghệ phần mềm, đã map theo mục lục yêu cầu.

## Cách compile

Trên Overleaf:

1. Upload toàn bộ file zip.
2. Mở `main.tex`.
3. Chọn compiler `pdfLaTeX`.
4. Bibliography dùng `Biber`.
5. Compile theo chu trình: pdfLaTeX → Biber → pdfLaTeX → pdfLaTeX.

## File cần sửa nhiều nhất

- `Preamble/metadata.tex`: thông tin bìa, tên đề tài, GVHD, sinh viên.
- `FrontMatter/summary_vi.tex`: tóm tắt tiếng Việt.
- `FrontMatter/abstract_en.tex`: abstract tiếng Anh.
- `FrontMatter/abbreviations.tex`: danh mục từ viết tắt.
- `Sections/*.tex`: nội dung từng chương.
- `References/refs.bib`: tài liệu tham khảo.

## Cấu trúc hiện tại

- Tóm tắt báo cáo
- Abstract
- Mục lục
- Danh mục từ viết tắt
- Danh mục hình
- Danh mục bảng
- Chương 1 -- Giới thiệu đề tài
- Chương 2 -- Phân tích yêu cầu
- Chương 3 -- Kiến thức nền tảng
- Chương 4 -- Công nghệ và quyết định lựa chọn
- Chương 5 -- Thiết kế hệ thống
- Chương 6 -- Hiện thực và triển khai hệ thống
- Chương 7 -- Kiểm thử hệ thống
- Chương 8 -- Kết luận và hướng phát triển
- Tài liệu tham khảo
- Phụ lục

## Đề xuất chuẩn hóa báo cáo còn 70 trang nội dung chính

> **Trạng thái:** Chương 1, Chương 2 và Chương 4 đã được chuẩn hóa. Việc gộp,
> rút gọn và sắp xếp các chương còn lại theo phương án tám chương đang tiếp tục
> được thực hiện.

Hạn mức 70 trang chỉ tính tám chương nội dung chính. Bìa, lời cam đoan, lời cảm
ơn, tóm tắt, mục lục, các danh mục, tài liệu tham khảo và phụ lục không tính vào
hạn mức này.

| Chương | Nội dung đề xuất | Số trang dự kiến | Khoảng trang |
|---|---|---:|---:|
| 1 | Giới thiệu đề tài | 2 | 1--2 |
| 2 | Phân tích yêu cầu | 10 | 3--12 |
| 3 | Cơ sở lý thuyết | 7 | 13--19 |
| 4 | Công nghệ | 4 | 20--24 |
| 5 | Thiết kế hệ thống | 20 | 25--44 |
| 6 | Hiện thực và triển khai hệ thống | 13 | 45--57 |
| 7 | Kiểm thử và đánh giá hệ thống | 11 | 58--68 |
| 8 | Kết luận và hướng phát triển | 2 | 69--70 |
| | **Tổng cộng** | **70** | |

Cấu trúc Chương 7 đề xuất theo hai nhóm chức năng, trong phạm vi 11 trang nội dung (trang 58--68; trang 57 là trang mở đầu chương):

| Mục | Nội dung | Số trang dự kiến |
|---|---|---:|
| 7.1 | Mục tiêu, phạm vi và chiến lược kiểm thử | 0,5 |
| 7.2 | Thiết kế đánh giá các chức năng AI | 3,0 |
| 7.3 | Kết quả đánh giá các chức năng AI | 2,5 |
| 7.4 | Kiểm thử các chức năng ngoài AI Service: thành phần, cách tiến hành và kết quả | 2,5 |
| 7.5 | Kiểm thử yêu cầu phi chức năng: phương pháp và kết quả | 1,5 |
| 7.6 | Tổng hợp, truy vết yêu cầu và thảo luận sau kiểm thử | 1,0 |
| | **Tổng cộng** | **11,0** |

Nội dung chi tiết nên sắp xếp như sau:

- **7.1 Mục tiêu, phạm vi và chiến lược kiểm thử:** phân biệt hai nhóm chức năng AI và ngoài AI; nêu câu hỏi đánh giá, phạm vi, môi trường, tiêu chí nghiệm thu và cách tổ chức bằng chứng.
- **7.2 Thiết kế đánh giá các chức năng AI:** trình bày bảng dữ liệu đánh giá cho tìm kiếm văn bản, tìm kiếm hình ảnh, tìm kiếm kết hợp và trợ lý hội thoại/RAG; mô tả nguồn dữ liệu, cách chia tập, cách xây dựng và kiểm soát ground truth, các chỉ số đánh giá, baseline, ablation, so sánh rerank và kiểm tra độ bền.
- **7.3 Kết quả đánh giá các chức năng AI:** báo cáo kết quả theo từng chức năng và từng cấu hình; so sánh với baseline, phân tích tác động của ablation/rerank, kết quả kiểm tra độ bền và chốt cấu hình AI được lựa chọn.
- **7.4 Kiểm thử các chức năng ngoài AI Service:** trình bày theo trình tự các thành phần được kiểm thử, cách tiến hành và kiểm soát ca kiểm thử, sau đó báo cáo kết quả Backend, đồng bộ dữ liệu, end-to-end và fallback.
- **7.5 Kiểm thử yêu cầu phi chức năng:** mô tả môi trường và phương pháp đo hiệu năng, bảo mật, khả dụng, quan sát và tương thích; sau đó đối chiếu kết quả với các nhóm NFR.
- **7.6 Tổng hợp, truy vết yêu cầu và thảo luận sau kiểm thử:** lập ma trận FR/NFR với ca kiểm thử và kết quả; thảo luận sau khi đã có kết quả AI và ngoài AI, nêu giới hạn, điều kiện sử dụng kết quả và phạm vi nghiệm thu của hệ thống.

Để giữ nội dung chính tập trung, các bảng dữ liệu đánh giá đầy đủ, danh sách nhãn ground truth, log, danh sách ca kiểm thử, response mẫu và ảnh chụp bằng chứng nên chuyển sang Phụ lục F. Trong nội dung chính cần giữ lại bảng mô tả tập đánh giá, các bảng kết quả đối chiếu theo từng chức năng và nhận định có ảnh hưởng đến kết luận. Riêng mục 7.3 nên dùng `subsubsection` để tách Text Search, Image Search, Hybrid Search và Conversational AI, qua đó trình bày rõ baseline, ablation và cấu hình được lựa chọn.

Cấu trúc Chương 1 đã chốt và triển khai:

- 1.1 Lý do chọn đề tài.
- 1.2 Mục tiêu.
- 1.3 Phạm vi.
- 1.4 Cấu trúc báo cáo.

Cấu trúc Chương 2 đã chốt và triển khai:

- 2.1 Khảo sát hiện trạng và nhu cầu -- sử dụng dữ liệu thứ cấp và tài liệu chính thức, không khảo sát người dùng trực tiếp.
- 2.2 Phân tích các bên liên quan.
- 2.3 Phân tích quy trình nghiệp vụ.
- 2.4 Yêu cầu chức năng.
- 2.5 Yêu cầu dữ liệu và yêu cầu phi chức năng.
  - 2.5.1 Yêu cầu dữ liệu.
  - 2.5.2 Yêu cầu phi chức năng.
- 2.6 Sơ đồ Usecase.
- 2.7 Sơ đồ hoạt động.

Cấu trúc Chương 4 đã chốt và triển khai trong `Sections/04-CongNgheVaQuyetDinhLuaChon.tex`:

- 4.1 Tiêu chí và tổng quan lựa chọn công nghệ.
- 4.2 Công nghệ ứng dụng và dữ liệu nghiệp vụ.
- 4.3 Công nghệ AI và xử lý dữ liệu đa phương thức.
- 4.4 Công nghệ truy hồi, xếp hạng và quản lý trạng thái.
- 4.5 Công nghệ triển khai và tổng hợp quyết định.

Nội dung Chương 4 được rút gọn theo hạn mức khoảng 5 trang (trang 22--26). Các
nguyên lý embedding, truy hồi, RAG và cấu hình triển khai chi tiết không lặp lại ở
chương này; chúng được trình bày ở Chương 3, Chương 5, Chương 6 hoặc phụ lục.

Phạm vi nội dung Chương 2 và phụ lục:

| Phần | Giữ trong Chương 2 | Chuyển sang phụ lục |
|---|---|---|
| Khảo sát hiện trạng | Số liệu thị trường, hành vi mua sắm, đối chiếu chức năng và nhu cầu hệ thống | Không chuyển sang phụ lục; không có phiếu khảo sát người dùng hoặc dữ liệu thô do đề tài tự thu thập |
| Các bên liên quan | Bảng vai trò, mục tiêu và tương tác chính | Không lặp lại |
| Yêu cầu chức năng | Bảng tổng hợp theo nhóm chức năng | Danh mục yêu cầu chức năng chi tiết |
| Yêu cầu dữ liệu | Nhóm dữ liệu, mục đích và nơi lưu trữ | Không lặp lại trong Phụ lục A; từ điển dữ liệu có thể đưa vào Phụ lục C sau |
| Yêu cầu phi chức năng | Tiêu chí và ngưỡng nghiệm thu | Không lặp lại trong Phụ lục A; bằng chứng kiểm thử có thể đưa vào Phụ lục F sau |
| Phân tích quy trình nghiệp vụ | Mô tả ngắn gọn các quy trình chính | Chỉ giữ các quy trình có sơ đồ minh họa |
| Sơ đồ Usecase | Ba sơ đồ phía khách hàng, quản trị viên và AI Service | Một bảng tổng hợp đặc tả Usecase; không tách bảng chi tiết cho từng Usecase |
| Sơ đồ hoạt động | Đặt hàng COD, tìm kiếm đa phương thức và tư vấn nhiều lượt | Chỉ giữ các sơ đồ không xuất hiện trong chương chính: xác nhận đơn COD và đồng bộ chỉ mục AI |

Tệp chính của chương là `Sections/02-PhanTichYeuCau.tex`. Hai tệp chương cũ đã
được chuyển thành tài liệu chi tiết tại `Appendices/` và được nạp sau tài liệu
tham khảo.

Định hướng biên tập:

- Khai thác yêu cầu và Phân tích hệ thống đã được gộp thành Chương 2.
- Đổi Kiến thức nền tảng thành Cơ sở lý thuyết.
- Gộp Cài đặt hệ thống và Hiện thực hệ thống thành Chương 6.
- Giữ trong nội dung chính các kiến trúc, luồng xử lý, kết quả và nhận định quan
  trọng; chuyển tài liệu mang tính tra cứu hoặc bằng chứng chi tiết sang phụ lục.
- Giữ phần Cấu trúc báo cáo ở mục 1.4 dưới dạng một đoạn ngắn; không đưa
  nội dung này vào phần Tóm tắt.
- Mỗi chương nên có từ ba đến sáu mục lớn; hạn chế chia sâu hơn cấp mục `x.y.z`.
- Đoạn mã dài, đặc tả đầy đủ, bộ ảnh giao diện, cấu hình triển khai và kết quả thô
  nên đặt trong phụ lục.

Các nhóm phụ lục hiện tại và dự kiến:

- Phụ lục A -- Yêu cầu chức năng chi tiết.
- Phụ lục B -- Mô hình phân tích, đặc tả Usecase và sơ đồ hoạt động chi tiết.
- Phụ lục C -- Thiết kế dữ liệu và từ điển dữ liệu (đã triển khai).
- Phụ lục D -- Giao diện và hướng dẫn sử dụng (dự kiến).
- Phụ lục E -- Cài đặt và triển khai (dự kiến).
- Phụ lục F -- Kiểm thử, dữ liệu thực nghiệm và bằng chứng (dự kiến).
- Phụ lục G -- API và mã nguồn tiêu biểu (dự kiến).

## Khi nộp bản chính thức

Các hướng dẫn nội bộ đã được loại khỏi danh sách file biên dịch chính; thư mục
`Sections` chỉ giữ các chương và tệp phụ trợ đang được sử dụng.

## Quy tắc citation

Từ Chương 1 đến hết báo cáo, phần nào lấy ý tưởng, dữ liệu, nhận định, định nghĩa hoặc mô tả từ tài liệu khác thì phải trích dẫn trực tiếp tại đoạn đó bằng `\parencite{key}` hoặc `\textcite{key}`.
