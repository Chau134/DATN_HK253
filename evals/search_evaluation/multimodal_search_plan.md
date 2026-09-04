# Multimodal Search Evaluation Plan

Plan này đánh giá chất lượng Multimodal Search bằng ảnh + text. Đây là bộ test độc lập với
Text Search và Image Search.

## Metrics

> Tham khảo cho giai đoạn sau, chưa thực thi trong bản đầu (xem mục "Ngoài phạm vi bản này").

- `Precision@K`
- `Recall@K`
- `NDCG@K`
- `MRR`

Khuyến nghị K:

- `K = 5, 10, 20`

## 1. Chuẩn bị Product Database

Multimodal Search dùng chung **Product Evaluation View** mô tả ở
[README](./README.md#product-evaluation-view). Không giả định `products` có cột phẳng `category`,
`color`, `price`, `is_active` — các field này phải được map từ schema MySQL thật.

Yêu cầu dữ liệu:

- Product Database đã ETL và chuẩn hóa.
- Mỗi sản phẩm dùng cho Multimodal Search phải có ít nhất 1 ảnh hợp lệ.
- Metadata hỗ trợ query text và ground truth lấy từ Product Evaluation View: `category` (JOIN
  `product_categories` → `categories`), `brand` (`brand_name`), `color` (hợp nhất `base_colour`/
  `colour1`/`colour2` + `_vi`), `material`, `gender`, `price` (JOIN `product_prices`),
  `usage` (`product_usage(_vi)`), `description`.
- Ảnh lấy từ `product_images` (`image_url`, `sort_order`), fallback `products.main_image`.

Output đề xuất (các field logic của View):

```csv
product_id,product_name,category,brand,color,material,gender,price,usage,image_id,image_url
```

## 2. Query Coverage

Quy trình:

1. Lấy Product Database khoảng 5000 sản phẩm hoặc toàn bộ nếu ít hơn 5000.
2. Lọc sản phẩm có ít nhất 1 ảnh hợp lệ.
3. Dùng Stratified Sampling theo `category` để tránh multimodal query lệch về một nhóm sản phẩm.
4. Với mỗi sản phẩm, chọn ngẫu nhiên 1 ảnh.
5. Sinh câu text bổ sung bằng template từ metadata.
6. Người kiểm tra chỉnh sửa nếu cần.
7. Chốt 100 Multimodal Queries.

Ghi chú:

- Query text nên bổ sung điều kiện khớp ảnh, ví dụ màu, chất liệu, dịp sử dụng, ngân sách.
- Nên có nhóm text bổ sung không mâu thuẫn với ảnh trong bản đầu.
- Có thể thêm nhóm text mâu thuẫn với ảnh ở vòng sau để test conflict handling, nhưng cần nhãn riêng.

> **Bước kiểm tra khả thi ground truth (bắt buộc trước khi chốt query).** Vì query multimodal ràng
> buộc cả điều kiện ảnh lẫn text, nếu text bổ sung quá hẹp (ví dụ ghép brand + màu hiếm + khoảng giá
> nhỏ) thì database có thể không còn sản phẩm relevant nào ngoài chính source product → ground truth
> rỗng hoặc chỉ có self-match, không đánh giá được. Với mỗi query, chạy thử candidate SQL kết hợp
> ảnh+text: nếu số candidate hợp lệ quá ít, nới điều kiện text hoặc đổi source product trước khi chốt.

## 3. Query Set

Template đề xuất:

- `tìm sản phẩm giống ảnh, màu {color}`
- `tìm {category} giống ảnh cho {gender}`
- `tìm sản phẩm giống ảnh, chất liệu {material}`
- `tìm đồ giống ảnh phù hợp {usage}`
- `tìm {brand} hoặc sản phẩm tương tự ảnh`
- `tìm sản phẩm giống ảnh trong khoảng {price_bucket}`

Schema:

```csv
query_id,mode,source_product_id,image_id,image_url,query_text,category,brand,color,material,gender,price_bucket,usage,manual_status,notes
```

Trong đó:

- `mode = multimodal`
- `source_product_id`: sản phẩm chứa ảnh query.
- `query_text`: điều kiện bổ sung đi kèm ảnh.

## 4. Ground Truth

Ground truth của Multimodal Search là sản phẩm relevant theo cả ảnh và text.
SQL chỉ sinh candidate, không quyết định ground truth cuối cùng.

```text
Ground Truth Generation
  -> Read Query Image Product Metadata
  -> Extract Text Attributes
  -> Combine Image Attributes And Text Conditions
  -> Generate SQL
  -> Candidate Relevant Products
  -> Assign Relevance Grade
  -> Manual Validation
  -> Final Ground Truth
```

### Quy trình

1. Lấy metadata từ ảnh query.
2. Phân tích điều kiện bổ sung trong text.
3. Kết hợp điều kiện ảnh và điều kiện text.
4. Sinh SQL để lấy Candidate Relevant Products.
5. Gán relevance grade theo cả ảnh và text.
6. Kiểm tra thủ công nếu điều kiện ảnh và text mâu thuẫn hoặc quá hẹp.
7. Chốt Final Ground Truth.

Schema:

```csv
query_id,mode,relevant_product_id,relevance_grade,match_reason,source,review_status,notes
```

Relevance grade:

- `3`: đúng sản phẩm nguồn hoặc sản phẩm rất giống ảnh và thỏa text bổ sung.
- `2`: giống ảnh và thỏa phần lớn điều kiện text.
- `1`: giống ảnh hoặc thỏa text nhưng thiếu một phần quan trọng.
- `0`: không liên quan, thường không lưu vào final ground truth.

## 5. Tiêu chí chấp nhận bản đầu

Phạm vi bản này chỉ tới sinh testcase + ground truth:

- Có 100 multimodal queries.
- Mỗi query có ảnh hợp lệ và text bổ sung.
- Mỗi query có ít nhất 1 relevant product trong final ground truth (đã qua bước kiểm tra khả thi ở mục 2).
- Dùng Stratified Sampling theo category.
- Có seed/version rõ ràng cho sampling và chọn ảnh.
- Ít nhất 20% ground truth được kiểm tra thủ công ở vòng đầu.

## 6. Ngoài phạm vi bản này (làm sau)

Các phần dưới đây CHƯA làm trong bản đầu, chỉ giữ làm định hướng khi hệ thống search sẵn sàng:

- **Chạy Multimodal Search**: gọi endpoint `service-ai` `POST /search/hybrid` bằng `image_url` + `query_text`,
  lưu top K, chuẩn hóa output `run_id,query_id,mode,rank,product_id,score,raw_score_json`; cố định version
  database + image/text embedding/index/model; lưu config `top_k`, filter, modality weights, threshold, reranker;
  log lỗi ảnh không tải được hoặc text parse sai.
- **Metrics**: Precision@K, Recall@K, NDCG@K, MRR (K=5/10/20).
- **Báo cáo**: breakdown theo category, color, material, usage, price_bucket, và theo loại text bổ sung;
  danh sách query text làm lệch khỏi ảnh, query ảnh đúng nhưng text filter sai, query top-1 sai nhưng top-10 đúng.
- **Đánh giá theo modality weights**: hệ hybrid thật trộn điểm theo trọng số (image 0.45 / text 0.35 /
  filter 0.15 / business 0.05). Giai đoạn sau nên đánh giá riêng theo các bộ trọng số để biết khi nào ảnh
  thắng, khi nào text filter thắng — đây là giá trị cốt lõi của multimodal, để lại như định hướng, chưa thực thi.

