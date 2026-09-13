# Hybrid Search Evaluation

Bộ đánh giá chính thức cho endpoint `POST /search/hybrid` gồm 100 truy vấn trên
snapshot 1.000 sản phẩm. Mỗi truy vấn dùng ảnh làm tham chiếu về nhận dạng và
kiểu dáng; văn bản mô tả thuộc tính cần thay đổi hoặc giữ lại.

## Thiết kế dữ liệu

Tập truy vấn gồm các biến đổi có kiểm soát về màu sắc, chất liệu, mục đích sử
dụng và giá. Các trường hợp khó kết hợp hai nhóm yêu cầu. Ảnh tham chiếu đã được
duyệt về nhận dạng sản phẩm và thay đổi thị giác dự kiến.

Các đầu vào chính nằm trong `data/`:

- `product_snapshot.csv`: snapshot sản phẩm dùng để đối chiếu.
- `multimodal_queries.csv`: 100 truy vấn ảnh--văn bản.
- `reference_image_requirements.csv`: nguồn và yêu cầu đối với ảnh tham chiếu.
- `product_constraint_snapshot_v2_20260911.csv`: thuộc tính chuẩn hóa phục vụ
  đánh giá ràng buộc.

## Hợp đồng đánh giá ràng buộc

`constraint_satisfaction@5` chỉ kiểm tra những thuộc tính được nêu trong
`query_text`. Một sản phẩm đạt khi thỏa đồng thời tất cả trường người dùng hỏi;
không tự bổ sung điều kiện màu, chất liệu, mục đích hoặc giá nếu truy vấn không
nêu. Danh sách mục đích sử dụng thông thường áp dụng phép ANY; chỉ áp dụng ALL
khi câu có diễn đạt như “tất cả”, “đồng thời” hoặc “cả ba”. Category và độ giống
kiểu dáng thuộc relevance/NDCG, không được thêm ngầm vào satisfaction.

Evaluator tính lại ràng buộc độc lập từ truy vấn và snapshot, không sử dụng cờ
pass do API trả. `request_conditioned_ndcg@5` giữ grade 0--3 nhưng đặt gain bằng
0 cho sản phẩm vi phạm ràng buộc của chính truy vấn.

## Baseline và ablation cuối cùng

Năm cấu hình được chạy trên cùng query set, ground truth, Top-K và seed:

1. Text-only.
2. Image-only.
3. Fusion, rerank tắt.
4. Image-conditioned, usage ANY, rerank tắt.
5. Image-conditioned, usage ANY, rerank bật.

Ground truth cuối là hợp Top-5 của năm cấu hình, gồm 1.627 cặp đã duyệt. Các
khoảng tin cậy paired bootstrap dùng 10.000 lần lấy mẫu lại theo truy vấn với
seed 42.

## Artifact chính thức

- `reports/image_conditioned_20260910/review_pool/reviewed_v4_five_way_corrected/`:
  ground truth cuối, nguồn review và kết quả validation.
- `reports/hybrid_ablation_five_way_gt_v4_20260911.json`: kết quả đầy đủ và
  metric theo từng truy vấn.
- `reports/hybrid_ablation_five_way_gt_v4_20260911.csv`: bảng tổng hợp máy đọc.
- `reports/hybrid_ablation_five_way_gt_v4_20260911.md`: bảng kết quả phục vụ báo cáo.
- `reports/image_conditioned_20260910/rollout_20260911/`: manifest, quality gate
  và bằng chứng tải của cấu hình triển khai.
- `reports/product_constraint_snapshot_v2_20260911.json`: thông tin kiểm tra
  snapshot ràng buộc.

Cấu hình được chọn là Image-conditioned, usage ANY, rerank tắt: Strict Hit@5
0,980; NDCG@5 0,873; Request-conditioned NDCG@5 0,958; thỏa ràng buộc@5 0,990;
P95 tuần tự 2.105,2 ms.

Các artifact review tạm, lần chạy lỗi và kết quả trước GT v4 đã được loại bỏ sau
khi khóa kết quả chính thức ngày 11/09/2026.
