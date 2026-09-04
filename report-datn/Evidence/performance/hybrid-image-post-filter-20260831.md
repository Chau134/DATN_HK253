# Baseline Hybrid: ảnh + post-filter văn bản

- Ngày chạy: 2026-08-31
- Run ID: `hybrid-image-post-filter-20260831`
- Bộ kiểm thử: 100 truy vấn Hybrid phản thực có kiểm soát.
- Candidate đầu vào: Top-20 từ artifact Image-only đã đóng băng ngày 2026-08-28.
- Post-filter: đối chiếu chính xác sau chuẩn hóa đối với category, color, material, price bucket và usage; giữ nguyên thứ tự similarity ảnh.
- Không sử dụng Text Search, fusion trọng số, business boost hoặc reranker.

## Ground truth và coverage

Post-filter tạo 249 dòng kết quả và còn 4 truy vấn rỗng. Top-5 sau lọc có 21 cặp query--product chưa nằm trong 633 nhãn Hybrid ban đầu. Cả 21 cặp đều đã có nhãn approved trong ground truth Image Search ghép cặp, nên được chuyển nhãn với provenance `approved_image_ground_truth_transfer`; không phát sinh nhãn luật hoặc yêu cầu người duyệt mới.

Ground truth mở rộng có 654 nhãn approved, phân bố grade 0/1/2/3 là 22/491/40/101. Số cặp chưa có nhãn sau audit bằng 0.

## Kết quả

| Cấu hình | Strict Hit@5 | Graded NDCG@5 | Graded Recall@5 | Thỏa toàn bộ ràng buộc@5 | Query đạt@5 | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Image + text post-filter | 0,960 | 0,890 | 0,895 | 0,960 | 0,960 | 1,299 giây |
| Fusion, rerank tắt | 0,920 | 0,855 | 0,858 | 0,446 | 0,960 | 0,892 giây |

Paired bootstrap 10.000 mẫu, seed 42, tính theo `fusion_no_rerank - image_post_filter`:

- Strict Hit@5: -0,040; CI 95% [-0,100; +0,020].
- Graded NDCG@5: -0,035; CI 95% [-0,091; +0,018].
- Graded Recall@5: -0,037; CI 95% [-0,099; +0,023].
- Thỏa toàn bộ ràng buộc@5: -0,514; CI 95% [-0,587; -0,439].
- Query đạt@5: 0,000; CI 95% [-0,050; +0,050].

Chênh lệch Hit@5, NDCG@5 và Recall@5 giữa hai cấu hình chưa có ý nghĩa thống kê ở mức 95%; post-filter giữ toàn bộ ràng buộc tốt hơn rõ rệt. Fusion tắt rerank có P95 thấp hơn 0,407 giây.

## Giới hạn diễn giải

Đây là baseline replay sử dụng các trường ràng buộc có cấu trúc đã đóng băng trong fixture, vì vậy gần với một post-filter oracle. Nó không đo sai số trích xuất ràng buộc từ ngôn ngữ tự nhiên và không thay thế pipeline Hybrid production. Kết quả dùng để hoàn chỉnh đối chứng thuật toán, chưa phải căn cứ tự động thay đổi cấu hình triển khai.

## Tái hiện

```powershell
cd evals/search_evaluation/hybrid
python scripts/07b_build_image_post_filter.py
python scripts/13_compare_ablation.py `
  --ground-truth-csv data/ground_truth_multimodal_post_filter_20260831.csv `
  --run "image_only=data/search_results_image_only_20260828.csv;reports/hybrid_responses_image_only_20260828.jsonl" `
  --run "text_only=data/search_results_text_only_20260828.csv;reports/hybrid_responses_text_only_20260828.jsonl" `
  --run "image_post_filter=data/search_results_image_post_filter_20260831.csv;reports/hybrid_responses_image_post_filter_20260831.jsonl" `
  --run "fusion_no_rerank=data/search_results_fusion_no_rerank_20260828.csv;reports/hybrid_responses_fusion_no_rerank_20260828.jsonl" `
  --run "fusion_rerank=data/search_results_fusion_rerank_20260828.csv;reports/hybrid_responses_fusion_rerank_20260828.jsonl"
```

Unit test runner và comparator: `9 passed`.
