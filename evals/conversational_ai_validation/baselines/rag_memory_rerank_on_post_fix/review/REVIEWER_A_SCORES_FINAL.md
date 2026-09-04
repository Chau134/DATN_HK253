# Kết quả chấm Reviewer A hậu sửa

Reviewer A đã chấm 45 ca có đầu ra/context thay đổi. Điểm 1–5 và hard gate
được áp dụng theo `evals/conversational_ai_validation/review/RUBRIC.md`.

| ID | Câu hỏi | F | G | R | C | T | CR | RC | H | Hard gate | Kết quả | Nhận xét |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| conv-ord-0004-t0 | Tìm Áo kiểu màu Màu cát / Đen | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Chỉ trả mẫu khớp chính xác tổ hợp Màu cát / Đen; không chèn màu gần. |
| conv-rec-0007-t0 | Tôi cần Váy & Đầm màu Đen cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba đầm đều đúng màu Đen, danh mục và giới tính. |
| conv-flt-0003-t1 | màu trắng thì sao? | 5 | 5 | 4 | 4 | 4 | 4 | NA | 4 | product_exists=pass | Đạt | Giữ đúng danh mục; hai mẫu Trắng khớp hoàn toàn, mẫu thứ ba Trắng ngà chỉ gần màu yêu cầu. |
| conv-flt-0002-t1 | rẻ hơn nữa có không? | 5 | 5 | 5 | 5 | 5 | 5 | NA | 5 | product_exists=pass | Đạt | Giữ đúng danh mục và màu tổ hợp; thông báo không có mẫu rẻ hơn thay vì đưa kết quả sai giá. |
| conv-flt-0004-t0 | Tìm Áo kiểu màu Xanh dương nhạt | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba áo kiểu đều có màu Xanh dương nhạt và đúng evidence. |
| conv-cmp-0008-t0 | So sánh Áo kiểu màu đen và trắng dáng quây đính sequin chấm bi và Áo sơ mi màu đen tay ngắn thắt nơ ở gấu. | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Đủ hai sản phẩm và kết luận khác nhau đúng về danh mục, màu, chất liệu. |
| conv-rec-0005-t0 | Tôi cần Váy & Đầm màu Đỏ rượu vang cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Trả đúng mẫu Đỏ rượu vang, không bổ sung các mẫu Đỏ thường lệch sắc độ. |
| conv-ord-0001-t0 | Tìm Quần dài màu Nâu / Trắng ngà | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Hai quần đều khớp chính xác tổ hợp Nâu / Trắng ngà. |
| critical-product-001 | Shop có Áo khoác Sao Hỏa phiên bản 2099 không? Nếu không có dữ liệu hãy nói rõ. | 5 | 5 | 4 | 5 | NA | NA | 5 | 4 | product_exists=pass, clarification_or_refusal=pass | Đạt | Từ chối đúng sản phẩm không tồn tại trước khi gợi ý. Một áo khoác phù hợp; hai gợi ý áo kiểu hơi xa nhu cầu nên relevancy/helpfulness=4. |
| conv-rec-0001-t0 | Tôi cần Bodysuit màu Đen cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba Bodysuit đều đúng màu Đen, giới tính Nữ và đúng evidence. |
| conv-flt-0005-t0 | Tìm Áo thun màu Vani | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Trả đúng mẫu Áo thun màu Vani duy nhất trong context. |
| conv-cmp-0001-t0 | So sánh Bodysuit ôm màu nâu cổ V không tay và Quần dài ống suông màu nâu chồn lưng vừa. | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Đủ hai sản phẩm, thuộc tính và kết luận giống/khác tường minh. |
| conv-rec-0018-t0 | Tôi cần Áo thun màu Nâu thuốc lá cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Trả đúng mẫu Nâu thuốc lá duy nhất, không chèn màu nâu gần. |
| conv-rec-0015-t0 | Tôi cần Áo kiểu màu Đen cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba áo kiểu đều đúng màu Đen, danh mục và giới tính. |
| conv-cmp-0007-t0 | So sánh Áo kiểu màu đen tay bồng thêu hoa và Áo kiểu màu đen và trắng vải voan họa tiết tay bồng. | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Đủ hai áo kiểu; kết luận giống/khác đúng evidence. |
| conv-cmp-0004-t0 | So sánh Đầm mini cúp ngực màu đen và trắng chấm bi kèm thắt lưng và Đầm sơ mi midi màu nâu thuốc lá cài cúc gấu xếp ly. | 3 | 3 | 2 | 1 | 1 | NA | NA | 2 | product_exists=pass | Không đạt | Chỉ truy hồi được đầm nâu thuốc lá nên không thực hiện so sánh; yêu cầu người dùng kiểm tra lại hai tên dù ground truth xác nhận cả hai. |
| conv-cmp-0006-t0 | So sánh Áo hai dây màu trắng ngà và nâu phối vải thêu và Áo sát nách màu nâu chocolate cotton cổ cao. | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Đủ hai sản phẩm; nêu đúng điểm giống về danh mục và khác về màu/chất liệu. |
| conv-rec-0008-t0 | Tôi cần Váy & Đầm màu Hồng pastel cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Trả đúng mẫu Hồng pastel duy nhất thay vì chèn các sắc hồng khác. |
| conv-ord-0005-t1 | mẫu đầu tiên thế nào? | 5 | 5 | 5 | 5 | 5 | 5 | NA | 5 | product_exists=pass | Đạt | Tham chiếu đúng sản phẩm đầu tiên và mô tả đúng evidence. |
| conv-flt-0001-t1 | màu đen thì sao? | 5 | 5 | 5 | 5 | 5 | 5 | NA | 5 | product_exists=pass | Đạt | Giữ đúng danh mục Quần dài và thay màu sang Đen; cả ba kết quả phù hợp. |
| conv-ord-0002-t0 | Tìm Váy & Đầm màu Xám than | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Hai đầm đều thuộc dải màu Xám than và đúng danh mục. |
| conv-rec-0010-t0 | Tôi cần Áo hai dây, áo sát nách & áo yếm màu Vàng ánh kim cho Nữ, có gợi ý nào không? | 1 | 1 | 2 | 1 | 1 | NA | NA | 2 | product_exists=pass | Không đạt | Báo không tìm thấy, nhưng reference xác nhận có áo hai dây màu Vàng ánh kim đính sequin. |
| conv-rec-0020-t0 | Tôi cần Áo thun màu Trắng cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba áo thun đều đúng màu Trắng, danh mục và giới tính. |
| conv-rec-0003-t0 | Tôi cần Quần dài màu Nâu sọc cho Nữ, có gợi ý nào không? | 1 | 1 | 2 | 1 | 1 | NA | NA | 2 | product_exists=pass | Không đạt | Báo không tìm thấy, nhưng reference xác nhận có Quần dài màu nâu sọc mảnh có quai đai. |
| conv-ord-0004-t1 | cái thứ 2 thì sao? | 2 | 2 | 2 | 1 | 1 | 1 | NA | 2 | product_exists=pass | Không đạt | Lượt trước có danh sách nhưng chỉ có một mẫu. Cần nói không có mẫu thứ hai; câu trả lời lại khẳng định không có danh sách trước đó. |
| conv-ord-0003-t0 | Tìm Áo hai dây, áo sát nách & áo yếm màu Hồng | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba sản phẩm đúng danh mục và màu Hồng. |
| conv-cmp-0003-t0 | So sánh Đầm màu đen cotton kẻ sọc cổ cao tay dài và Đầm mini cổ yếm màu nâu hở lưng xẻ tà viền ren. | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | So sánh đúng danh mục, màu và chất liệu; có kết luận giống/khác. |
| conv-fact-0019-t0 | Áo thun màu vàng nhạt crop xếp ly gấu bồng phù hợp cho nam hay nữ? | 2 | 2 | 1 | 1 | NA | NA | NA | 2 | product_exists=pass | Không đạt | Không trả lời giới tính Nữ dù reference và required evidence đã xác định; hỏi lại thông tin không cần làm rõ. |
| conv-ord-0002-t1 | mẫu đầu tiên thế nào? | 5 | 5 | 5 | 5 | 5 | 5 | NA | 5 | product_exists=pass | Đạt | Tham chiếu đúng sản phẩm đầu tiên và mô tả đúng evidence. |
| conv-cmp-0002-t0 | So sánh Quần dài ống loe màu đen và trắng vân nổi cúc hình trái tim và Quần dài ống loe màu trắng ngà vải twill co giãn khóa kim loại. | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Đủ hai sản phẩm; nêu đúng điểm giống về danh mục và khác về màu/chất liệu. |
| conv-flt-0002-t0 | Tìm Váy & Đầm màu Đỏ / Trắng | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba đầm đều mang tổ hợp đỏ/trắng hoặc biến thể trắng ngà/đỏ phù hợp. |
| conv-rec-0016-t0 | Tôi cần Áo sơ mi màu Hồng / Trắng cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba áo sơ mi đều khớp chính xác tổ hợp Hồng / Trắng. |
| conv-ord-0005-t0 | Tìm Áo thun màu Nâu chocolate | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba áo thun đều khớp chính xác màu Nâu chocolate. |
| critical-product-002 | Cho tôi thông tin sản phẩm Váy Mặt Trăng mã MC-999999; nếu không tìm thấy hãy nói rõ. | 5 | 5 | 5 | 5 | NA | NA | 5 | 5 | product_exists=pass, clarification_or_refusal=pass | Đạt | Từ chối đúng mã không tồn tại; ba gợi ý thay thế đều là Váy & Đầm có trong context. |
| conv-flt-0004-t1 | màu đen thì sao? | 5 | 5 | 5 | 5 | 5 | 5 | NA | 5 | product_exists=pass | Đạt | Giữ đúng danh mục Áo kiểu và chuyển sang các mẫu có màu Đen. |
| conv-ord-0001-t1 | cái thứ 2 thì sao? | 5 | 5 | 5 | 5 | 5 | 5 | NA | 5 | product_exists=pass | Đạt | Tham chiếu đúng sản phẩm thứ hai và mô tả đúng evidence. |
| conv-flt-0001-t0 | Tìm Quần dài màu Nâu melange | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba quần dài đều đúng màu Nâu melange và đúng evidence. |
| conv-rec-0019-t0 | Tôi cần Áo thun màu Nâu đậm cho Nữ, có gợi ý nào không? | 1 | 1 | 2 | 1 | 1 | NA | NA | 2 | product_exists=pass | Không đạt | Báo không tìm thấy, nhưng reference xác nhận có Áo thun màu nâu đậm tay ngắn xẻ sau. |
| conv-cmp-0005-t0 | So sánh Áo kiểu dệt kim màu cam cổ polo gấu phồng và Áo sát nách màu đỏ dâu cổ thuyền tối giản. | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Đủ hai sản phẩm và kết luận đúng các điểm khác về danh mục, màu, chất liệu. |
| conv-flt-0003-t0 | Tìm Áo hai dây, áo sát nách & áo yếm màu Nâu | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba sản phẩm đúng danh mục áo hai dây/sát nách/yếm và màu Nâu. |
| conv-flt-0005-t1 | rẻ hơn nữa có không? | 5 | 5 | 5 | 5 | 5 | 5 | NA | 5 | product_exists=pass | Đạt | Giữ đúng ràng buộc Áo thun màu Vani và không bịa mẫu rẻ hơn. |
| conv-ord-0003-t1 | cái thứ 3 có gì đặc biệt? | 5 | 5 | 5 | 5 | 5 | 5 | NA | 5 | product_exists=pass | Đạt | Tham chiếu đúng sản phẩm thứ ba và mô tả đúng evidence. |
| conv-rec-0013-t0 | Tôi cần Áo kiểu màu Trắng cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba áo kiểu đều đúng màu Trắng, danh mục và giới tính. |
| conv-rec-0002-t0 | Tôi cần Quần dài màu Chàm cho Nữ, có gợi ý nào không? | 5 | 5 | 3 | 4 | 3 | NA | NA | 3 | product_exists=pass | Không đạt | Hai mẫu đầu đúng màu Chàm; mẫu thứ ba màu Khaki vi phạm ràng buộc màu chính. |
| conv-rec-0006-t0 | Tôi cần Váy & Đầm màu Đỏ cho Nữ, có gợi ý nào không? | 5 | 5 | 5 | 5 | 5 | NA | NA | 5 | product_exists=pass | Đạt | Ba đầm đều đúng màu Đỏ, danh mục và giới tính. |

Tổng hợp riêng 45 ca hậu sửa: **38/45 đạt**, **7/45 không đạt** theo Reviewer A.
