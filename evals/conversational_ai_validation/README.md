# Conversational AI Validation

## Quy trình chính: master-80-v2 và đối chứng A–D

Bộ nghiệm thu hiện hành gồm đúng 80 câu: 68 câu từ bộ hội thoại ban đầu và toàn bộ 12 ca critical.
Pilot 40 câu và manifest ba baseline cũ chỉ được giữ để truy vết, không phải đầu vào nghiệm thu mới.

Trạng thái hiện tại:

1. Ground truth 80 câu đã được duyệt đầy đủ; approval nằm tại
   `review/master_80/ground_truth_approval_summary.json`.
2. Cấu hình D hậu sửa (RAG + memory + rerank bật) đã chạy 80/80. Dữ liệu review đã thực hiện trước đây
   vẫn được lưu để truy vết, nhưng không còn là điều kiện của quy trình nghiệm thu hiện hành.
   Bộ kết quả chuẩn duy nhất nằm trong `baselines/rag_memory_rerank_on_post_fix` và dùng hậu tố
   `final_validated` cho output tự động.
3. A = LLM thuần, B = RAG không memory và C = RAG + memory, rerank tắt đã chạy đủ 80/80 ngày
   27/08/2026. Các packet V3, V1 và V4 được giữ nguyên như artifact tùy chọn, không cần hoàn tất để nghiệm thu.
4. So sánh tự động A--D nằm tại `reports/baseline_comparison.*` và dùng
   `baselines/manifest_master_80_results.json` để ghép đúng D hậu sửa. Đây là đầu vào chính của báo cáo.

`scripts/12_run_ablation_variant.py` chạy từng cấu hình và đối chiếu `/health/ready` với manifest để
ngăn gắn nhầm nhãn. A/B cô lập session và user ID ở từng lượt; C/D giữ nguyên phiên nhiều lượt.

Bộ kiểm định này là lớp bổ sung cho `../conversational_ai_evaluation`. Bộ cũ chạy chatbot/RAG và
tạo metric kỹ thuật; bộ này chuẩn hóa ground truth, áp dụng tiêu chí cứng cho dữ liệu nhạy cảm và
so sánh bốn cấu hình A--D trên cùng tập 80 câu.

Không gọi `token_f1_relevancy` trong file nguồn là “answer relevancy” khi viết báo cáo. Tên trình bày
đúng là **mức tương đồng token-F1 với câu trả lời tham chiếu**.

## Quy trình nghiệm thu tự động

Mỗi cấu hình A--D phải chạy đủ 80 câu trên cùng ground truth đã duyệt, snapshot và phiên bản code.
Runner xác nhận cấu hình thực tế qua `/health/ready`, lưu response/trace, tính Grounding, Context
Precision, Context Recall và chấm 12 ca critical. Token-F1 chỉ dùng để chẩn đoán độ giống từ vựng.

Kết luận cấu hình dựa trên so sánh A--D và các hard gate; không yêu cầu packet đánh giá thủ công.
Các script/file review vẫn được giữ nguyên để có thể dùng lại như một đợt kiểm tra bổ sung trong tương lai.

## Tiêu chí cứng

Các cột `critical_*` chỉ nhận `pass`, `fail` hoặc `NA`:

- `critical_price`: không bịa hoặc dùng sai giá/giảm giá.
- `critical_stock`: không bịa tồn kho, trạng thái còn/hết hàng hoặc size.
- `critical_product_exists`: không giới thiệu sản phẩm không tồn tại; sản phẩm được nêu phải có trong
  nguồn/context phù hợp.
- `critical_policy`: không khẳng định chính sách khi evidence không hỗ trợ.
- `critical_clarification_or_refusal`: câu không thể trả lời phải từ chối hoặc yêu cầu làm rõ.

Chỉ một tiêu chí cứng `fail` cũng khiến ca không đạt, bất kể điểm trung bình.

## Điều kiện nghiệm thu

- Chạy đủ 80/80 câu và có evaluation trace/context hợp lệ.
- Grounding, Context Precision và Context Recall được tính trên cùng ground truth đã duyệt.
- 12/12 ca critical phải vượt hard gate tự động; một lỗi giá, tồn kho, sản phẩm giả hoặc chính sách là không đạt.
- So sánh A--D dùng cùng snapshot và chỉ thay thành phần cần ablation.
- Token-F1 không phải điều kiện pass/fail.

## Baseline

`baselines/manifest.json` định nghĩa ba cấu hình bắt buộc:

1. LLM không RAG.
2. RAG không memory.
3. RAG + search + memory đầy đủ.

Template từ dữ liệu sản phẩm là cấu hình tùy chọn. Mỗi cấu hình phải chạy cùng question set, snapshot,
prompt/model (trừ thành phần bị loại bỏ), seed và môi trường. Đặt `rag_metrics_summary.json` và
`critical_gate_summary.json` vào thư mục tương ứng trong `baselines/`. Script không sinh kết luận
nhân quả khi baseline bắt buộc còn thiếu.

## Ca nhạy cảm về giá, tồn kho và chính sách

Pilot 40 câu lấy từ bộ cũ không có câu hỏi trực tiếp về giá/tồn kho, vì vậy hai gate này không được
xem là đã đo. Bộ 12 ca bổ sung nằm tại `data/critical_cases.csv`. Khi AI Service evaluation đang chạy
với `ASSISTANT_EVAL_TRACE_ENABLED=true`, thực thi bằng runner hiện có:

```powershell
python ../conversational_ai_evaluation/scripts/07_run_rag_eval.py `
  --questions-csv data/critical_cases.csv `
  --snapshot-csv ../conversational_ai_evaluation/data/product_snapshot.csv `
  --output-csv reports/critical_gate_responses.csv `
  --metadata-json reports/critical_gate_run_metadata.json `
  --endpoint http://localhost:8000/assistant/chat `
  --require-evaluation-trace
python scripts/05_score_critical_gates.py
```

Script đối chiếu giá và tồn kho với `retrieved_context` tại thời điểm chạy, không hard-code kết quả kỳ
vọng vào báo cáo. Chỉ một hard gate tự động `fail` cũng làm cấu hình không đạt phần critical.

## Output dùng cho báo cáo

- `reports/automatic_breakdown.csv`: metric theo category và difficulty.
- `reports/human_validation_summary.json`: artifact lịch sử/tùy chọn, không phải đầu vào bắt buộc.
- `reports/token_f1_calibration.csv`: artifact chẩn đoán, không dùng để quyết định pass/fail.
- `reports/baseline_comparison.csv`: bảng đối chứng.
- `reports/report_ready_summary.md`: diễn giải tổng hợp.
- `reports/report_fragment.tex`: bảng/đoạn LaTeX để review trước khi đưa vào chương 09.

## Kiểm thử mã nguồn

```powershell
python -m pytest test_validation.py
```
