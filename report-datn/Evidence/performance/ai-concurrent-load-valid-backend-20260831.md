# AI concurrent load — valid Backend gateway rerun (2026-08-31)

## Mục tiêu

Chạy lại bài tải sau khi loại bỏ xung đột cổng với Uvicorn cục bộ, bảo đảm request đi vào AI container và Assistant lấy product context thành công từ Spring Boot Backend.

## Cấu hình

- AI target: `http://127.0.0.1:8000`, Docker instance `a7b127140d36433890ff85d5afd42313`.
- Backend target từ container: `http://host.docker.internal:8080`.
- Mô hình tải: closed workload, 6 worker, 180 giây, chu kỳ 5 giây.
- Phân bổ: 2 Text, 2 Hybrid và 2 Assistant worker.
- Ngưỡng: Text/Hybrid P95 <= 5 giây; Assistant P95 <= 30 giây; error rate <= 1%; correlation ID coverage = 100%.

Preflight Assistant trả HTTP 200, có 3 product ID, không warning, có correlation ID và không làm tăng `spring_boot_unavailable`.

## Kết quả

| Workload | Thành công | Text P95 | Hybrid P95 | Assistant P95 | Correlation ID | Backend fallback | RAM peak | Kết luận |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Control | 212/212 | 4,206 s | 2,739 s | 6,320 s | 100% | 0 | 453,1 MiB | PASS |
| Representative | 216/216 | 1,843 s | 0,864 s | 5,318 s | 100% | 0 | 510,4 MiB | PASS |

Backend integration evidence:

- Control: 63 lượt gọi product context; 132 cache hit và 13 cache miss.
- Representative: 72 lượt gọi product context; 201 cache hit và 15 cache miss.
- Không có `spring_boot_unavailable`, `springboot_request_failed` hoặc `springboot_response_failed` trong cửa sổ kiểm thử.
- AI vẫn `ready=true`; Backend vẫn `UP` sau tải.
- Ở workload representative, RAM tăng từ 464,0 MiB lên 470,7 MiB, với peak tạm thời 510,4 MiB.

## Kết luận

Hai workload đều đạt toàn bộ acceptance check trên đúng AI container và có Backend product context hoạt động. Các artifact rerun trước đó dùng khi Uvicorn cục bộ cùng chiếm cổng 8000 không được dùng làm bằng chứng tài nguyên container hoặc Backend gateway.

## Artifact

- `ai-concurrent-load-valid-backend-control-20260831.json`
- `ai-concurrent-load-valid-backend-representative-20260831.json`
