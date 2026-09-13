# Text Semantic Challenge — Final v4

Bộ semantic challenge kiểm tra từ đồng nghĩa, cách nói hội thoại, vật liệu tương
đương và mô tả được diễn đạt lại. Bản v4 reduced được khóa trước khi so sánh
Vector Search, BM25 và ablation rerank.

Artifact cuối:

- `configs/keyword_bm25_v4_reduced.toml`;
- `reports/metrics_keyword_bm25_v4_reduced.{json,csv}`;
- `reports/search_results_keyword_bm25_v4_reduced.csv`;
- `reports/compare_keyword_vs_vector_v4_reduced_no_rerank.{json,md}`;
- `reports/compare_vector_no_rerank_vs_rerank_v4_reduced.{json,md}`.

Các phiếu được giữ trong `review/` là nhãn semantic, lựa chọn canonical reduced
và review chênh lệch của chính v4. Script tạo/finalize vẫn nằm trong `scripts/`;
các output v1 và v3 đã được loại bỏ.
