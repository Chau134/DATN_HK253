# Image Search Evaluation

Bộ chính thức đánh giá cùng 100 sản phẩm dưới hai điều kiện ảnh:

- `simple`: ảnh catalog `DETAIL_1`;
- `challenging`: 66 ảnh người mẫu và 34 ảnh ngoài trời.

Ground truth cuối gồm 2.935 cặp đã duyệt. Ngưỡng liên quan nhị phân là grade từ
2 trở lên. Hai lượt dùng cùng embedding, index và Top-20; chỉ thay ảnh truy vấn
để đo độ bền. Các JSON metric chính thức lưu aggregate, breakdown và đủ 100 dòng
`per_query` cho mỗi điều kiện.

## Artifact chính thức

- `simple/reports/metrics_paired_simple.{json,csv}`;
- `challenging/reports/metrics_paired_challenging.{json,csv}`;
- `simple/reports/paired_exact_metrics.json` và `paired_exact_per_query.csv`;
- `simple/reports/paired_similarity_comparison.{json,md}`;
- các tệp `metrics_paired_*_latency.{json,csv}` của hai điều kiện.

Kết quả Simple/Challenging lần lượt là Exact Hit@5 1,000/0,970, NDCG@5
0,853/0,810 và Exact MRR 0,990/0,950. Mã nguồn sinh dữ liệu, chạy truy hồi và
tính metric được giữ trong `scripts/`; metadata ảnh nguồn nằm trong `data/`.

Các báo cáo standalone ngày 22/08 và pooling/review trung gian đã được loại bỏ
sau khi khóa bộ paired ngày 28/08/2026.
