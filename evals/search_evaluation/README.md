# Search Evaluation

Thư mục này chứa bộ kế hoạch đánh giá Search cho 3 mode độc lập:

- [Text Search Plan](./text_search_plan.md)
- [Image Search Plan](./image_search_plan.md)
- [Multimodal Search Plan](./multimodal_search_plan.md)

Mỗi plan có query set, ground truth và rủi ro riêng. Báo cáo tổng hợp sẽ được xây dựng sau khi
phần dự án ổn định và có thể merge kết quả của 3 mode bằng `run_id` và `mode`.

> **Phạm vi bản này:** cả 3 plan chỉ triển khai tới bước **sinh testcase (query set) + ground truth**.
> Phần *chạy search, tính metrics và xuất report* CHƯA làm vì hệ thống search của dự án đang hoàn thiện;
> các section liên quan được giữ làm tài liệu tham khảo và đánh dấu "Ngoài phạm vi bản này (làm sau)".

Text Search, Image Search, và Multimodal Search đã có workflow thực thi riêng trong các thư mục
[text](text), [image](image), và [multimodal](multimodal), gồm sampler, query generator, candidate
ground truth, và cấu hình seed đầu vào.

## Mục tiêu chung

> Phạm vi bản này chỉ tới **sinh testcase + ground truth**. Phần chạy search, tính metrics và xuất
> report CHƯA làm vì hệ thống dự án đang hoàn thiện — xem "Thứ tự triển khai đề xuất".

- Tạo query set và ground truth chất lượng, có thể tái chạy, có seed/version, và có bước kiểm tra
  thủ công — làm nền cho evaluation khi hệ thống search sẵn sàng.
- Chuẩn hóa dữ liệu sản phẩm từ Product Database (MySQL denormalized) qua một Product Evaluation View
  dùng chung cho cả 3 mode.
- Định hướng cho giai đoạn sau: so sánh các phiên bản search model, embedding, ranking, filtering,
  reranking, hybrid search; xuất báo cáo metrics theo mode và theo nhóm thuộc tính như category,
  brand, color, material, gender, price, usage.

## Product Evaluation View

Database thật là MySQL denormalized (catalog Zara, nguồn
`service-api-ecommerce/src/main/resources/schema.sql`). Schema thật KHÔNG có các cột phẳng như
`products.category`, `products.color`, `products.price`, `products.is_active`. Vì vậy cả 3 mode dùng
chung một **Product Evaluation View** — lớp chuẩn hóa map từ schema thật sang các field logic dùng
trong evaluation. Mọi plan con phải trỏ field về View này thay vì giả định cột trực tiếp.

Mapping từ schema thật sang field logic:

| Field logic (eval) | Nguồn thật trong DB |
| --- | --- |
| `product_id` | `products.id` |
| `product_name` | `products.product_display_name` (+ `product_display_name_vi`) |
| `brand` | `products.brand_name` (nằm trực tiếp trên `products`, không phải bảng riêng) |
| `color` | hợp nhất từ `products.base_colour`, `colour1`, `colour2` (+ các `_vi`) — nhiều cột, không phải 1 |
| `material` | `products.material` (+ `material_vi`) |
| `gender` | `products.gender` (+ `gender_vi`) |
| `usage` | `products.product_usage` (+ `product_usage_vi`) |
| `price` | JOIN bảng riêng `product_prices` (không nằm trên `products`) |
| `category` | many-to-many: JOIN `product_categories` → `categories`, ưu tiên `category_name_vi`, chọn theo `category_level` |
| `description` | `products.description` (+ `description_vi`) |
| `is_active` | suy ra từ `product_attributes` (`attr_key='flag:active'`) hoặc từ variant còn active — KHÔNG phải cột trực tiếp trên `products` |
| ảnh | `product_images` (`image_type`, `sort_order`, `image_url`) + fallback `products.main_image` |

Lưu ý ảnh: `product_images.image_type` trong DB thật chỉ có 2 giá trị `hero` và `gallery`, chưa phải
semantic type phục vụ evaluation (xem Image Search Plan).

Nếu dữ liệu có variant, cần chốt đánh giá ở cấp `product_id` hay `variant_id`. Khuyến nghị bản đầu:
đánh giá ở cấp `product_id`.

## Output search chuẩn hóa

> Phạm vi bản này chỉ tới sinh testcase + ground truth. Section này giữ làm **tài liệu tham khảo cho
> giai đoạn sau** (khi hệ thống search sẵn sàng), chưa thực thi trong bản đầu.

Mỗi mode nên lưu kết quả search theo format chung:

```csv
run_id,query_id,mode,rank,product_id,score,raw_score_json
```

Trong đó:

- `run_id`: mã lần chạy evaluation.
- `query_id`: mã query trong query set.
- `mode`: `text`, `image`, hoặc `multimodal`.
- `rank`: thứ hạng kết quả, bắt đầu từ 1.
- `product_id`: ID sản phẩm hệ thống trả về.
- `score`: điểm search/ranking nếu có.
- `raw_score_json`: điểm phụ để debug, ví dụ vector score, filter score, rerank score.

## Cấu trúc thư mục đề xuất

```text
evals/search_evaluation/
  README.md
  text_search_plan.md
  image_search_plan.md
  multimodal_search_plan.md
  configs/
    text_search.yaml
    image_search.yaml
    multimodal_search.yaml
  data/
    text_queries.csv
    image_queries.csv
    multimodal_queries.csv
    ground_truth_text.csv
    ground_truth_image.csv
    ground_truth_multimodal.csv
  scripts/
    text/
      01_sample_products.py
      02_generate_queries.py
      03_generate_ground_truth_candidates.py
    image/
      01_sample_products.py
      02_generate_queries.py
      03_generate_ground_truth_candidates.py
    multimodal/
      01_sample_products.py
      02_generate_queries.py
      03_generate_ground_truth_candidates.py
```

## Metrics chung

> Tham khảo cho giai đoạn sau, chưa thực thi trong bản đầu (xem "Thứ tự triển khai đề xuất").

- `Precision@K`
- `Recall@K`
- `NDCG@K`
- `MRR`
- `mAP` cho Image Search
- `Empty Result Accuracy` và `False Positive Rate@K` cho negative queries

Khuyến nghị K:

- `K = 5, 10, 20`

## Nguyên tắc Ground Truth chung

SQL chỉ dùng để sinh candidate relevant products, không phải ground truth cuối cùng.

```text
Ground Truth Generation
  -> Extract Attributes
  -> Generate SQL
  -> Candidate Relevant Products
  -> Assign Relevance Grade
  -> Manual Validation
  -> Final Ground Truth
```

Schema chung:

```csv
query_id,mode,query_type,relevant_product_id,relevance_grade,match_reason,source,review_status,notes
```

Trong đó:

- `query_type`: `positive` hoặc `negative`.
- `relevance_grade`: `0, 1, 2, 3`.
- `source`: `sql_candidate`, `manual_added`, `manual_removed`, `manual_approved`.
- `review_status`: `pending`, `approved`, `rejected`.

## Thứ tự triển khai đề xuất

Phạm vi bản này (làm ngay):

1. Chốt schema `Product Evaluation View`.
2. Chốt 3 file config riêng cho text, image, multimodal.
3. Viết sampling/query/ground-truth scripts theo từng mode.
4. Review query set và ground truth thủ công.

Ngoài phạm vi bản này — làm khi hệ thống search sẵn sàng:

5. Viết runner gọi hệ thống Search theo từng mode.
6. Viết metric calculator dùng chung nhưng có nhánh xử lý riêng theo mode.
7. Xuất report từng mode.
8. Merge report tổng hợp theo `run_id`.
