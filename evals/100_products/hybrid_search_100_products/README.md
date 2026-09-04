# Hybrid search evaluation – 100 sản phẩm

Suite chính dùng đúng snapshot `database/100.sql` và gồm **25 testcase** cần human review:

| Nhóm | Số case | Ý nghĩa |
|---|---:|---|
| `available-image` | 5 | Tìm sản phẩm có kiểu dáng giống ảnh sản phẩm có sẵn |
| `different-color` | 5 | Giống kiểu dáng ảnh nhưng theo màu trong câu chữ |
| `different-material` | 5 | Giống kiểu dáng ảnh nhưng theo chất liệu trong câu chữ |
| `specific-use` | 5 | Giống ảnh và phù hợp mục đích sử dụng |
| `external-image` | 5 | Tìm sản phẩm database bằng ảnh tham chiếu ngoài catalog |

Mọi `image_source_product_id`, candidate và ground-truth ID đều phải thuộc snapshot 100 sản phẩm.
Mỗi ảnh nguồn chỉ xuất hiện trong một testcase. Ground truth không được tự động approve từ metadata:
reviewer phải đối chiếu trực quan trước khi chạy live.

## Quality metrics and ablation

The review evaluator records graded NDCG@5, metadata-candidate Hit@5,
visually-approved Hit@K, and explicit constraint satisfaction for
category/color/material. Run all three retrieval variants on the same 25 cases:

```powershell
.\.venv\Scripts\python.exe evals\hybrid_search_100_products\run_review_eval.py --ablation
```

The text-only, image-only, and constrained-hybrid comparison is written to
`review/ablation_summary.json`.

## Script

- `prepare_ground_truth_review.py`: sinh cố định 25 case, candidate review và danh sách link còn thiếu.
- `run_review_eval.py`: chỉ chạy khi đủ ảnh và toàn bộ case đã được human review thành `APPROVED`.
- `run_eval.py`: baseline kỹ thuật 100 ảnh catalog cùng sản phẩm; giữ riêng để kiểm tra aligned-modality,
  không dùng thay cho bộ 25 case review.

## Sinh bộ review

Từ repository root:

```powershell
.\.venv\Scripts\python.exe evals\hybrid_search_100_products\prepare_ground_truth_review.py
```

Đầu ra:

- `review/test_cases_pending_review.csv`: manifest 25 testcase.
- `review/ground_truth_candidates_pending_review.csv`: candidate lấy từ `database/100.sql`.
- `review/missing_image_links.csv`: đúng các product ID cần project owner cung cấp link.
- `review/generation_summary.json`: kiểm tra số case, phân bố, link và ID database.
- `review/image_sources.json`: nơi bổ sung URL theo `product_id`.

Thêm link mới vào `provided_images` trong `review/image_sources.json`, sau đó chạy lại generator.
Case và `image_source_product_id` giữ ổn định với cùng snapshot/seed.

## Review và chạy live

Quy trình review chi tiết nằm trong `review/README.md`. Khi cả 25 case đã có URL, có ít nhất một
ground truth được approve và có `review_status=APPROVED`:

```powershell
.\.venv\Scripts\python.exe evals\hybrid_search_100_products\run_review_eval.py
```

Runner từ chối manifest thiếu nhóm, thiếu ảnh, chưa approve hoặc chứa ground-truth ID ngoài database.
Report live được ghi vào `review/results.jsonl`, `review/result_summary.json` và
`review/assessment.md`, với breakdown riêng theo năm nhóm.

## Chạy baseline 100 ảnh catalog

```powershell
.\.venv\Scripts\python.exe evals\hybrid_search_100_products\run_eval.py --prepare-only
.\.venv\Scripts\python.exe evals\hybrid_search_100_products\run_eval.py
```

Baseline này đo Hit@1/3/5, MRR, lỗi HTTP, empty/duplicate, source và latency trên ảnh catalog cùng
sản phẩm. Nó phù hợp để bắt regression kỹ thuật nhưng không thay thế suite hybrid có xung đột
màu/chất liệu/use case.
