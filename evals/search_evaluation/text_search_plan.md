# Text Search Evaluation Plan

Plan này đánh giá chất lượng Text Search bằng query dạng văn bản. Đây là bộ test độc lập với
Image Search và Multimodal Search.

## 1. Chuẩn bị Product Database

Text Search dùng chung **Product Evaluation View** mô tả ở [README](./README.md#product-evaluation-view).
Không giả định `products` có cột phẳng `category`, `color`, `price`, `is_active` — các field này phải
được map từ schema MySQL thật.

Yêu cầu dữ liệu:

- Product Database đã ETL và chuẩn hóa.
- Có snapshot đánh giá build từ Product Evaluation View, gồm các field logic: `product_id`,
  `product_name`, `category`, `brand`, `color`, `material`, `gender`, `price`, `usage`, `description`,
  `is_active`.
- Mapping cụ thể (theo README):
  - `product_id = products.id`, `product_name = product_display_name(_vi)`, `brand = brand_name`.
  - `category`: JOIN `product_categories` → `categories` (ưu tiên `category_name_vi`, chọn theo
    `category_level`) — không phải `products.category`.
  - `color`: hợp nhất từ `base_colour`, `colour1`, `colour2` (+ các `_vi`) — nhiều cột, không phải một.
  - `usage`: chuẩn hóa từ `product_usage` / `product_usage_vi`.
  - `price`: JOIN bảng riêng `product_prices`.
  - `is_active`: suy ra từ `product_attributes` (`attr_key='flag:active'`) hoặc từ variant còn active —
    không phải cột trực tiếp.
- Chỉ lấy sản phẩm active/searchable nếu hệ thống search cũng chỉ trả về nhóm này.
- Tạo snapshot/version dữ liệu để evaluation có thể tái chạy.

Ghi chú hiện thực: `text/scripts/common.py` đã xử lý các alias cột này (ví dụ color lấy từ
`color|base_colour|base_colour_vi|colour1|colour1_vi`, usage từ `usage|product_usage|product_usage_vi`,
category enrich từ `product_categories`+`categories`), nên snapshot chỉ cần cung cấp đúng các cột nguồn.

Output đề xuất (các field logic của View):

```csv
product_id,product_name,category,brand,color,material,gender,price,usage,is_active
```

## 2. Query Coverage

Không dùng random sampling thuần cho 100 sản phẩm vì dễ lệch dataset.

Ví dụ lệch:

```text
100 sản phẩm random:
  80 áo
  15 quần
  5 váy
```

Nếu query set lệch như vậy, metrics sẽ phản ánh tốt nhóm áo nhưng không đủ đại diện cho quần, váy,
giày, túi, phụ kiện hoặc category nhỏ.

### Stratified Sampling

Dùng Stratified Sampling theo `category` sau khi đã chuẩn hóa từ snapshot join/mapping.

Quy trình:

1. Lấy toàn bộ sản phẩm đủ điều kiện evaluation.
2. Thống kê phân phối category đã chuẩn hóa.
3. Chọn category cần đánh giá.
4. Phân bổ số lượng sample cho từng category.
5. Trong mỗi category, random sản phẩm với seed cố định.
6. Nếu cần, stratify phụ theo brand, color, gender hoặc price_bucket.

Chiến lược phân bổ:

- Nếu số category ít: chia tương đối đều.
- Nếu số category nhiều: đặt min/max, ví dụ mỗi category tối thiểu 5 query, tối đa 20 query.
- Nếu category quá nhỏ: lấy toàn bộ hoặc gộp vào nhóm `other`.
- Lưu lại `sampling_seed`, `sampling_strategy`, và phân phối category.

> **Cảnh báo lỗi diversity ở bộ testcase hiện tại.** Bộ `data/text_queries.csv` đang có: 90 positive
> query nhưng chỉ sinh từ ~5 sản phẩm nguồn (toàn Zara Women, vài category), do `sampled_products.csv`
> đầu vào quá nhỏ. Đây đúng là kiểu lệch dataset mà mục này cảnh báo. Cần **chạy lại sampling trên snapshot
> đầy đủ (~2045 sản phẩm)** với `seed=42` để có coverage category thực sự, trước khi coi query set là hợp lệ.

## 3. Query Set

Đề xuất bản đầu:

```text
100 Text Queries:
  90 positive queries
  10 negative queries
```

### Positive Queries

Sinh từ metadata của sản phẩm được sample.

Template đề xuất:

- `{category} {color}`
- `{brand} {category}`
- `{category} chất liệu {material}`
- `{category} cho {gender}`
- `{category} {usage}`
- `{category} {color} dưới {price_bucket}`
- `{brand} {category} {color} cho {usage}`

Schema:

```csv
query_id,mode,query_type,source_product_id,query_text,category,brand,color,material,gender,price_bucket,usage,manual_status,notes
```

Trong đó:

- `mode = text`
- `query_type = positive`
- `source_product_id`: sản phẩm dùng để sinh query.

### Negative Queries

Negative queries là query cố ý không có sản phẩm phù hợp trong database.

Tỷ lệ đề xuất:

- Khoảng 10% query set.
- Với 100 text queries: 10 negative queries.

Ví dụ:

- `áo nike màu tím neon`
- `áo lông cừu Canada Goose`
- `giày trượt tuyết chống nước màu bạc`
- `váy cưới đính kim cương`
- `áo khoác da thật dưới 100k`

Mục đích:

- Đánh giá search có trả về sản phẩm sai khi không tồn tại sản phẩm phù hợp không.
- Đánh giá Precision trong tình huống expected result rỗng.
- Kiểm tra hệ thống có biết trả rỗng, hạ confidence, hoặc nói không tìm thấy sản phẩm phù hợp.

Với negative query:

- `source_product_id` để trống.
- `query_type = negative`.
- `expected_result = empty`.
- Cần manual validation để chắc database thật sự không có match hợp lệ.

## 4. Ground Truth

Ground truth của Text Search là danh sách sản phẩm relevant theo từng query positive.
Với negative query, ground truth là expected empty result.

SQL chỉ sinh candidate, không quyết định ground truth cuối cùng.

```text
Ground Truth Generation
  -> Extract Attributes
  -> Generate SQL
  -> Candidate Relevant Products
  -> Assign Relevance Grade
  -> Manual Validation
  -> Final Ground Truth
```

### Quy trình

1. Phân tích query thành attributes: category, brand, color, material, gender, price, usage.
2. Sinh SQL từ attributes.
3. Truy vấn Product Database để lấy Candidate Relevant Products.
4. Gán relevance grade cho candidate.
5. Manual validation: giữ, loại, hoặc thêm sản phẩm bị SQL bỏ sót.
6. Với negative query, xác nhận không có sản phẩm phù hợp.
7. Chốt Final Ground Truth.

Schema:

```csv
query_id,mode,query_type,relevant_product_id,relevance_grade,match_reason,source,review_status,notes
```

Relevance grade:

- `3`: đúng sản phẩm nguồn hoặc match đầy đủ category + brand + color + material.
- `2`: match category + ít nhất 2 thuộc tính quan trọng.
- `1`: match category + 1 thuộc tính quan trọng hoặc sản phẩm thay thế hợp lý.
- `0`: không liên quan, thường không lưu vào final ground truth.

Điểm cần nhấn mạnh:

- SQL có thể sai nếu metadata thiếu hoặc category quá rộng.
- Manual Validation là bước bắt buộc để biến candidate thành final ground truth.
- Negative query nếu bị hệ thống trả sản phẩm sẽ tính là false positive.

## 5. Tiêu chí chấp nhận bản đầu

- Có 100 text queries.
- Có khoảng 90 positive queries và 10 negative queries.
- Positive query có ít nhất 1 relevant product trong final ground truth.
- Negative query được xác nhận là expected empty result.
- Dùng Stratified Sampling theo category.
- Ít nhất 20% query/ground truth được kiểm tra thủ công ở vòng đầu.
- Chỉ cần sinh được testcase ổn định để dùng cho giai đoạn sửa chữa tiếp theo.

## 6. Trạng thái hiện thực

Pipeline sinh testcase đã có sẵn ở thư mục [text](text):

- `scripts/01_sample_products.py`: stratified sampling theo category.
- `scripts/02_generate_queries.py`: sinh 90 positive + 10 negative query.
- `scripts/03_generate_ground_truth_candidates.py`: sinh candidate ground truth để review.
- `scripts/04_run_search.py`: gọi `service-ai` `POST /search/text` cho từng query, lưu kết quả
  chuẩn hóa `run_id,query_id,mode,rank,product_id,score,raw_score_json`. Query lỗi được ghi 1 dòng
  lỗi (product_id rỗng, `raw_score_json` chứa `{"error": ...}`) và không làm dừng cả run.
- `scripts/05_compute_metrics.py`: tính Precision@K, Recall@K, NDCG@K, MRR cho positive query và
  Empty Result Accuracy / False Positive Rate@K cho negative query; xuất `reports/metrics_text.json`
  + `reports/metrics_text.csv`, có breakdown theo `category` và `price_bucket`.
- `scripts/common.py`: thư viện dùng chung (load/normalize sản phẩm với alias cột thật, sampling,
  query template, chấm relevance grade, gọi search, các hàm metric).

Việc cần làm để đạt tiêu chí bản đầu:

- Chạy lại `01_sample_products.py` trên **snapshot đầy đủ ~2045 sản phẩm** với `seed=42`. Bộ
  `text_queries.csv` hiện tại bị lỗi diversity (90 positive query chỉ sinh từ ~5 source product,
  toàn Zara Women) do `sampled_products.csv` đầu vào quá nhỏ — cần sinh lại.
- Thực hiện manual validation thật trên candidate ground truth (không chỉ auto-approve).

## 7. Runner + Metrics (đã hiện thực)

Điều kiện chạy: `service-ai` đang chạy (mặc định `http://localhost:8000`) và Qdrant đã có data index.

```bash
# 1. Chạy search cho toàn bộ query set
python scripts/04_run_search.py --base-url http://localhost:8000 --top-k 20

# 2. Tính metrics so với ground truth
python scripts/05_compute_metrics.py --k-values 5,10,20 --relevance-threshold 1
```

- Runner đọc `data/text_queries.csv`, ghi `data/search_results_text.csv`.
- Metrics đọc `search_results_text.csv` + `ground_truth_text.csv` (chỉ dòng `review_status=approved`),
  join `query_type`/`category`/`price_bucket` từ query set, ghi report vào `reports/`.
- `relevance_threshold=1` nghĩa là grade ≥ 1 tính là relevant cho Precision/Recall; NDCG dùng gain
  theo grade 0–3.

Response API thật trả `results[]` với `{product_id, score, source, rerank_score?}` (không phải
`products`/`ai_score`) — helper `json_response_from_text_search` trong `common.py` parse đúng theo
contract này.

Ngưỡng mục tiêu (tham chiếu từ `docs/text-search.md`): `Precision@5 >= 0.75`, `NDCG@10 >= 0.80`,
negative false-positive rate `<= 10%`.

