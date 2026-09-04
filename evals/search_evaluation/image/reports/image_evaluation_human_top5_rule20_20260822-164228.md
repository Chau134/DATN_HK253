# Image Search Evaluation — Human Top 5 + Rule Top 20

Run: `image-human-top5-rule20-20260822-164228`  
Ngày chạy: 22/08/2026  
Embedding: Amazon Bedrock, `cohere.embed-v4:0`

## Phạm vi ground truth

- 100 query, mỗi query có 20 candidate đã judge.
- Top 5: 500 cặp được người dùng review; 11 nhãn được sửa/điền sau audit trực quan.
- Rank 6–20: 1.500 cặp dùng rule bảo thủ `metadata_rule_v1`.
- Rule không tự gán grade 3. Grade 3 ngoài exact `product_id` chỉ có alias SKU 1322/1325 đã được kiểm tra thủ công.
- Relevant chính thức: `relevance_grade >= 2`.
- Phân bố: grade 0 = 985, grade 1 = 822, grade 2 = 92, grade 3 = 101.

Đây là rebaseline evaluation contract. Không so trực tiếp mAP/NDCG với report dùng ground truth rule cũ 2.529 dòng để kết luận model tăng hoặc giảm.

## Kết quả full run

- HTTP/search success: 100/100.
- Result rows: 2.000.
- 20 unique products/query: 100/100.
- Underfill rate @5/@10/@20: 0.

| Metric | @5 | @10 | @20 |
|---|---:|---:|---:|
| Precision | 0,2820 | 0,1660 | 0,0965 |
| Recall | 0,8462 | 0,9220 | 1,0000 |
| NDCG | 0,8571 | 0,8585 | 0,9324 |
| Fulfillment | 1,0000 | 1,0000 | 1,0000 |
| Exact Hit | 0,9900 | 1,0000 | 1,0000 |

- Exact Hit@1: `0,9800`.
- Exact MRR: `0,9861`.
- Precision@returned: `0,0965`.
- mAP: `0,8710`.

Precision@20 thấp không đồng nghĩa API trả thiếu: mỗi query chỉ có trung bình 1,93 candidate đạt grade >=2 trong pool 20 đã judge. Coverage đạt đủ 20/20. Recall@20 đạt 1,0 theo thiết kế vì ground truth được tạo từ chính Top 20 của run này, không phải vì đã chứng minh tìm đủ mọi sản phẩm relevant trong toàn catalog.

## Trường hợp cần theo dõi

- `q0029`: exact product 1431 ở rank 9; đây là regression case ưu tiên cho ranking.
- `q0088`: exact `product_id=1325` ở rank 2, nhưng rank 1 là `product_id=1322` cùng SKU catalog `04344152427`. Trải nghiệm SKU-level đúng ở rank 1, còn metric exact product-id vẫn tính rank 2.
- Hard có Exact Hit@5 `0,9697`, thấp hơn easy/medium và đúng bằng ngưỡng gate đề xuất.

## Giới hạn

Nhãn rank 6–20 là rule-assisted, chưa có review trực quan. Chúng phù hợp để chạy rebaseline hiện tại nhưng không thay thế review chéo nếu dùng report làm benchmark công bố hoặc quyết định thay model.

Đây là pooled evaluation lấy candidate từ chính run đang đánh giá. Recall@20 vì vậy bằng 1 theo construction; mAP/Recall chỉ phản ánh khả năng xếp hạng trong pool đã judge. Khi A/B một thuật toán mới, phải lấy hợp của candidate từ baseline và biến thể mới, review các candidate mới xuất hiện rồi mới so sánh tuyệt đối.
