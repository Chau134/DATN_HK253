# Kết quả tải AI nghiệm thu NFR-01 sau tối ưu

## Mục tiêu và môi trường

- Run ID: `AI-CONCURRENT-20260906-181508`.
- AI Service: container `service-ai`, instance `b05a9f35156040b2b29ecca7b0b7e679`.
- Spring Backend: `http://host.docker.internal:8080`, kết nối cơ sở dữ liệu đã có sẵn trong schema `DATN`; không nạp lại dữ liệu.
- Mô hình tải: closed workload, 6 worker trong 180 giây, chu kỳ 5 giây; mỗi luồng Text Search, Hybrid Search và Assistant dùng 2 worker.
- Ngưỡng nghiệm thu: P95 của từng luồng AI không quá 5 giây; error rate không quá 1%; correlation ID coverage đạt 100%; Assistant không được fallback.

Preflight của cả ba luồng trả HTTP 200 và response hợp lệ. Riêng Assistant trả 3 product ID, không có warning và không fallback.

## Kết quả

| Luồng | Thành công | Error rate | P50 | P95 | P99 | Cực đại | Kết luận |
|---|---:|---:|---:|---:|---:|---:|---|
| Text Search | 72/72 | 0% | 0,377 s | 1,412 s | 1,691 s | 1,903 s | Đạt |
| Hybrid Search | 72/72 | 0% | 0,480 s | 3,412 s | 5,678 s | 6,072 s | Đạt |
| Assistant | 72/72 | 0% | 0,700 s | 2,776 s | 9,704 s | 9,751 s | Đạt |
| Tổng | 216/216 | 0% | 0,509 s | 2,384 s | 5,989 s | 9,751 s | Đạt |

Các kiểm tra bổ sung đều đạt:

- Correlation ID coverage: 100%.
- Health trước và sau tải: `ready=true`, cùng một instance, các capability Text Search, Image Search và Assistant LLM đều sẵn sàng.
- Assistant gọi Spring Backend 72/72 lượt; cache ngữ cảnh sản phẩm ghi nhận 201 hit và 15 miss.
- Không tăng bất kỳ metric fallback Assistant nào trong thời gian đo.
- CPU P95 là 119,091%, CPU cực đại 168,58%; RAM cực đại 432,4 MiB.

So với workload đại diện ngày 31/08 có Assistant P95 5,318 giây, kết quả sau tối ưu còn 2,776 giây, giảm 2,542 giây, tương đương 47,8%. P99 và cực đại của Assistant vẫn cao hơn 5 giây, nên đây là chỉ số cần theo dõi ở các đợt tải dài hơn; tiêu chí NFR-01 hiện hành dùng P95 nên không ảnh hưởng kết luận nghiệm thu.

## Kết luận

Toàn bộ acceptance check của runner đều trả `true`. Cả ba luồng AI có P95 dưới 5 giây, không lỗi, đủ correlation ID và không fallback Assistant. NFR-01 đạt.

## Artifact

- `Evidence/performance/ai-concurrent-load-nfr01-final-20260907.json`
