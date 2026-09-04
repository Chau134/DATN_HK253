# Ground-truth review cho hybrid search

Manifest có đúng **5 nhóm × 5 testcase = 25 case**. Năm case `available-image` dùng ảnh catalog
database; 20 case còn lại dùng URL do project owner cung cấp. Hiện không còn link thiếu.

## Bổ sung link ảnh

1. Mở `missing_image_links.csv`.
2. Dùng `image_source_product_id`, tên sản phẩm và `catalog_image_for_reference` để chọn ảnh truy vấn.
3. Ảnh phải đáp ứng `image_requirement`.
4. Thêm URL vào `provided_images` của `image_sources.json` theo đúng product ID.
5. Chạy lại `prepare_ground_truth_review.py`.

Không sửa `image_source_product_id` trực tiếp trong CSV sinh ra. Mỗi ID chỉ dùng cho một testcase.

Với `different-color`, màu nhìn thấy trong ảnh phải khác `requested_color`. Với
`different-material`, chất liệu ảnh phải khác `requested_material` khi có thể xác minh. Với
`external-image`, URL nên là ảnh ngoài catalog; product ID chỉ dùng để cố định loại/kiểu sản phẩm
tham chiếu.

## Chốt ground truth

Trong `ground_truth_candidates_pending_review.csv`, so sánh ảnh truy vấn với
`candidate_catalog_image_url`:

- `APPROVE`, grade `3`: đúng kiểu dáng và đúng điều kiện text.
- `APPROVE`, grade `2`: thay thế hợp lý, đúng điều kiện text.
- `REJECT`, grade `1`: liên quan yếu.
- `REJECT`, grade `0`: không liên quan.

Quyết định review được lưu có version trong `ground_truth_approvals.json`. Generator kiểm tra ID/grade
rồi điền lại `review_decision`, `reviewed_relevance_grade`, `approved_product_ids` và
`review_status=APPROVED`; không sửa tay CSV sinh ra.

Runner chỉ chấp nhận khi:

- đủ 25 case và mỗi nhóm đúng 5;
- mọi case có URL HTTP(S);
- mọi case đã `APPROVED`;
- `approved_product_ids` không rỗng và toàn bộ ID thuộc `database/100.sql`.

Summary live còn báo/fail nếu bất kỳ kết quả trả về có `product_id` ngoài snapshot 100 sản phẩm.
