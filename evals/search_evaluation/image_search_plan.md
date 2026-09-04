# Image Search Evaluation Plan

Plan này đánh giá chất lượng Image Search bằng ảnh đại diện/truy vấn ảnh. Đây là bộ test độc lập
với Text Search và Multimodal Search.

> Phạm vi bản này chỉ tới sinh testcase + ground truth. Phần chạy search, metrics và báo cáo được
> gom ở mục "Ngoài phạm vi bản này (làm sau)" ở cuối file.

## 1. Chuẩn bị Product Database

Image Search dùng chung **Product Evaluation View** mô tả ở
[README](./README.md#product-evaluation-view). Không giả định `products` có cột phẳng `category`,
`color`, `price`, `is_active` — các field này phải được map từ schema MySQL thật.

Yêu cầu dữ liệu:

- Product Database đã ETL và chuẩn hóa.
- Mỗi sản phẩm dùng cho Image Search phải có ít nhất 1 ảnh hợp lệ.
- Ảnh phải truy cập được bằng URL hoặc có local cache.
- Metadata hỗ trợ ground truth lấy từ Product Evaluation View: `category` (JOIN
  `product_categories` → `categories`), `brand` (`brand_name`), `color` (hợp nhất `base_colour`/
  `colour1`/`colour2` + `_vi`), `material`, `gender`, `style` nếu có.
- Ảnh lấy từ `product_images` (`image_type`, `sort_order`, `image_url`), fallback `products.main_image`.
- Lưu ý quan trọng: `product_images.image_type` trong DB thật chỉ có 2 giá trị `hero` và `gallery`
  (không có front/back/detail...). Đây chỉ là vai trò hiển thị, CHƯA phải semantic type phục vụ
  evaluation, nên cần `semantic_image_type` do reviewer gán (mục 2).

Output đề xuất:

```csv
product_id,product_name,category,brand,color,material,gender,source_image_id,image_url,db_image_type,sort_order,image_count
```

## 2. Query Coverage

Quy trình:

1. Lọc sản phẩm có ít nhất 1 ảnh hợp lệ từ toàn bộ catalog (~2045 sản phẩm).
2. Dùng Stratified Sampling theo `category` để chọn tập ứng viên nhỏ trước (ví dụ vài trăm ảnh),
   với seed cố định.
3. Với mỗi ảnh trong tập sample: lấy link gốc từ `product_images.image_url`, lưu `source_image_id`.
4. Mỗi testcase chỉ gồm 1 ảnh query duy nhất.
5. Reviewer chỉ gán `semantic_image_type` trên tập sample nhỏ này — KHÔNG annotate toàn bộ ảnh của
   catalog (không khả thi trong bản đầu).
6. Nếu cần cân bằng thêm, stratify phụ theo `semantic_image_type` sau khi đã có annotation của tập sample.
7. Chốt 100 Image Queries.

Ghi chú phạm vi: bước sinh testcase dừng ở đây (query set + annotation + ground truth). Việc chạy
search / tính metrics / report là giai đoạn sau.

### Một Testcase Chỉ Gồm 1 Ảnh

Với Image Search Evaluation, mỗi query/testcase chỉ dùng 1 ảnh query.

Nếu một sản phẩm có nhiều ảnh, có thể tạo nhiều testcase khác nhau:

```text
Product A
  -> image front     -> test img_001
  -> image back      -> test img_002
  -> image detail    -> test img_003
  -> image lifestyle -> test img_004
```

Lý do:

- Image Search đánh giá theo ảnh đầu vào cụ thể, không phải theo toàn bộ bộ ảnh của product.
- Ảnh `front` có thể search tốt nhưng ảnh `detail` hoặc `lifestyle` có thể search kém.
- Tách 1 ảnh/query giúp report biết chính xác loại ảnh nào làm giảm chất lượng.

### Semantic Image Type

Database hiện có `product_images.image_type`, nhưng giá trị có thể là `hero`/`gallery`.
Với evaluation, cần thêm `semantic_image_type` do reviewer gán khi xem link ảnh gốc.

Nếu chỉ random ảnh, rất dễ lấy gần như toàn ảnh front/hero. Trong khi Image Search cần test cả
ảnh người mẫu mặc, ảnh chi tiết, ảnh mặt sau, ảnh nghiêng, hoặc ảnh flatlay.

Danh sách `semantic_image_type` đề xuất:

| semantic_image_type | Ý nghĩa |
| --- | --- |
| `front` | ảnh chính/mặt trước sản phẩm |
| `back` | ảnh mặt sau sản phẩm |
| `side` | ảnh nghiêng |
| `detail` | ảnh cận cảnh chất liệu, họa tiết, nút, khóa, logo |
| `lifestyle` | người mẫu mặc hoặc dùng sản phẩm |
| `flatlay` | sản phẩm đặt trên nền/phẳng |
| `unknown` | chưa phân loại được |

File annotation đề xuất:

```csv
source_image_id,source_product_id,image_url,db_image_type,sort_order,semantic_image_type,image_quality,review_status,notes
```

Trong đó:

- `db_image_type`: giá trị từ database, ví dụ `hero` hoặc `gallery`.
- `semantic_image_type`: reviewer gán thủ công: `front`, `back`, `side`, `detail`,
  `lifestyle`, `flatlay`, hoặc `unknown`.
- `image_quality`: `good`, `medium`, `hard`.
 
Chiến lược coverage:

- Đảm bảo không để `front` chiếm quá nhiều query.
- Mỗi `semantic_image_type` quan trọng nên có số mẫu tối thiểu nếu dữ liệu đủ.
- **Hạ kỳ vọng theo dữ liệu thật**: DB chỉ có `hero`/`gallery`, gallery chưa chắc chứa đủ các góc
  `back`/`side`/`detail`. Bản đầu có thể chỉ phân biệt được nhóm hero vs gallery; các semantic type
  hiếm nếu thiếu thì ghi rõ trong `notes` của file annotation thay vì ép sampling.
- Có thể phân tầng chính theo `category`, sau đó phân tầng phụ theo `semantic_image_type`.

Ghi chú:

- Nên loại ảnh lỗi, ảnh quá nhỏ, ảnh không thấy rõ sản phẩm.
- Có thể giữ một nhóm ảnh khó để đánh giá robust, nhưng cần tag riêng.
- Reviewer có thể vào `image_url` gốc để gán nhãn semantic chính xác.

## 3. Query Set

Schema:

```csv
query_id,mode,source_product_id,source_image_id,image_url,db_image_type,semantic_image_type,category,brand,color,material,gender,image_quality,manual_status,notes
```

Trong đó:

- `mode = image`
- `source_product_id`: sản phẩm chứa ảnh query.
- `source_image_id`: ảnh query cụ thể dùng để đánh giá.
- `db_image_type`: giá trị hiện có trong database, ví dụ `hero` hoặc `gallery`.
- `semantic_image_type`: nhãn ảnh phục vụ evaluation: `front`, `back`, `side`, `detail`,
  `lifestyle`, `flatlay`, hoặc `unknown`.
- `image_quality`: `good`, `medium`, `hard`.

Lý do cần `source_image_id`:

- Một sản phẩm có thể có nhiều ảnh, ví dụ 6 ảnh gồm front, back, detail, lifestyle.
- Image Search đánh giá theo ảnh query cụ thể, không chỉ theo product.
- Nếu chỉ lưu `source_product_id`, không biết kết quả đang được đánh giá từ ảnh nào.
- `source_image_id` giúp debug trường hợp ảnh detail hoặc lifestyle làm search sai dù ảnh front đúng.

## 4. Ground Truth

Ground truth của Image Search là các sản phẩm giống hoặc tương tự ảnh query.
SQL chỉ sinh candidate, không quyết định ground truth cuối cùng.

```text
Query Image
  -> Identify Source Product
  -> Read Product Metadata
  -> Generate SQL
  -> Candidate Products
  -> Assign Relevance Grade
  -> Manual Validation
  -> Final Ground Truth
```

### Quy trình

1. Lấy `source_image_id` của query image.
2. Identify Source Product từ `source_image_id`.
3. Đọc metadata sản phẩm nguồn: category, brand, color, material, gender, style.
4. Sinh SQL tìm candidate sản phẩm cùng hoặc gần giống metadata.
5. Candidate Products chỉ là danh sách đề xuất ban đầu.
6. Gán relevance grade cho candidate.
7. Kiểm tra thủ công các case ảnh khó, ảnh nhiều màu, ảnh không rõ category.
8. Chốt Final Ground Truth.

Schema:

```csv
query_id,mode,source_product_id,source_image_id,relevant_product_id,relevance_grade,match_reason,source,review_status,notes
```

Relevance grade:

- `3`: đúng product hoặc đúng variant của product trong ảnh query.
- `2`: cùng category, rất giống kiểu dáng, màu gần giống, có thể thay thế hợp lý về mặt hình ảnh.
- `1`: cùng category nhưng khác style hoặc chỉ liên quan nhẹ. Ví dụ query là `Running Tee`,
  candidate là `Training Tee`.
- `0`: không liên quan hoặc khác category/style rõ ràng.

Quy ước để reviewer thống nhất:

- Grade 3 ưu tiên nhận diện đúng sản phẩm/variant, không chỉ "trông giống".
- Grade 2 là sản phẩm visual-similar đủ mạnh để người dùng có thể xem là lựa chọn tương tự.
- Grade 1 là cùng nhóm sản phẩm nhưng khác ý định hình ảnh chính.
- Grade 0 không lưu vào final ground truth, chỉ dùng khi review candidate bị loại.

> **Lưu ý về grade 3 = self-match.** Vì ảnh query lấy từ chính ảnh của sản phẩm nguồn, hầu như query
> nào cũng có ít nhất 1 grade-3 là chính sản phẩm nguồn. Điều này khiến grade 3 gần như "tự động đúng".
> Giá trị đánh giá thực sự nằm ở **grade 2 (visual-similar)** — khả năng tìm sản phẩm tương tự khác.
> Khi build ground truth, đừng chỉ dừng ở source product; phải chủ động tìm và gán grade 2 để bộ ground
> truth có ý nghĩa phân biệt.

## 5. Tiêu chí chấp nhận bản đầu

Phạm vi bản này chỉ tới sinh testcase + ground truth:

- Có 100 image queries.
- Mỗi query/testcase có đúng 1 ảnh query hợp lệ.
- Mỗi query lưu `source_image_id`, không chỉ `source_product_id`.
- Query set có file annotation gán `semantic_image_type` từ link ảnh gốc (trên tập đã sample).
- Query set có coverage theo `semantic_image_type` nếu dữ liệu ảnh cho phép; thiếu góc nào ghi rõ trong notes.
- Mỗi positive query có ít nhất 1 relevant product trong final ground truth, trong đó chủ động gán
  grade 2 (visual-similar) chứ không chỉ dừng ở source product grade 3.
- Có seed/version rõ ràng cho sampling và chọn ảnh.
- Ít nhất 20% ground truth được kiểm tra thủ công ở vòng đầu.

## 6. Ngoài phạm vi bản này (làm sau)

Các phần dưới đây CHƯA làm trong bản đầu, chỉ giữ làm định hướng khi hệ thống search sẵn sàng:

- **Chạy Image Search**: gọi endpoint `service-ai` `POST /search/image` bằng `image_url`/file ảnh, lưu
  top K, chuẩn hóa output `run_id,query_id,mode,rank,product_id,score,raw_score_json`; cố định version
  database + image embedding/index/model; lưu config `top_k`, filter, weights, threshold; log ảnh lỗi.
- **Metrics**: Precision@K, Recall@K, NDCG@K, mAP (K=5/10/20).
- **Báo cáo**: breakdown theo category, color, material, semantic_image_type, image_quality; danh sách
  ảnh lỗi, ảnh top-1 sai nhưng top-10 đúng, ảnh khó, semantic_image_type thiếu mẫu.
