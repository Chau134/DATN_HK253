# Kiểm thử soak checkout/payment qua Backend gateway

- Run ID: `CHECKOUT-PAYMENT-SOAK-20260901-031425`
- Bắt đầu: `2026-09-01T03:14:25Z`
- Cấu hình: 8 worker, 2 giờ, chu kỳ 5 giây/worker
- Workload: checkout preview, checkout idempotent, tạo COD idempotent, đọc payment và đọc order
- Cổng thanh toán ngoài: không gọi; COD kiểm định đường đi checkout/payment nội bộ

## Kết quả

- Hoàn tất đủ `7.200,447` giây; throughput `8,0 request/giây`.
- Tổng cộng `57.600/57.600` request thành công; error rate `0%` và không có error record.
- P50/P95/P99 tổng lần lượt là `26,396/48,863/68,006 ms`; cực đại `272,766 ms`.
- P95 checkout preview `60,439 ms`; checkout idempotent `48,291 ms`.
- P95 tạo COD idempotent `32,721 ms`; đọc payment `33,439 ms`; đọc order `44,425 ms`.
- Correlation ID đạt `100%` ở toàn bộ năm operation.
- Backend luôn `UP`; `120/120` mẫu tài nguyên không có health failure.
- HikariCP đạt cực đại `8/10` kết nối active và `0` pending.
- Heap đầu/cuối/cực đại là `144,537/170,966/192,735 MiB`; tăng ổn định theo median cửa sổ là `8,210 MiB`, dưới ngưỡng `128 MiB`.
- CPU tiến trình P95 `2,927%`, cực đại `17,582%`.
- Cleanup đạt `8/8`: toàn bộ payment COD test chuyển sang `CANCELLED`; đối soát DB không còn payment `PENDING` hay reservation hoạt động.
- Tất cả acceptance check đều `PASS`.

Artifact máy đọc: `checkout-payment-soak-2h-20260901.json`.
