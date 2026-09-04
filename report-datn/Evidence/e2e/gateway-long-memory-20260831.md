# Kiểm thử memory phiên dài qua Backend gateway

- Ngày chạy: 2026-08-31
- Phạm vi Backend: `MockMvc -> AiAssistantController -> AiAssistantChatServiceImpl -> RestAiServiceClient -> HTTP boundary của AI Service`.
- Phạm vi AI đối chứng: endpoint FastAPI `/assistant/chat` với workflow memory thật trong bộ integration test.

## Kịch bản qua gateway

Bài kiểm thử `AiAssistantGatewayLongMemoryTest` gửi 10 request HTTP vào `/api/assistant/chat`:

- Phiên A có 7 lượt duy nhất; lượt 7 được gửi lại một lần với cùng `request_id` để kiểm tra idempotency.
- Phiên B có 2 lượt xen kẽ với phiên A để kiểm tra isolation.
- Backend phải forward nguyên vẹn `session_id`, `request_id`, `turn_sequence`; danh tính khách được chuẩn hóa thành `guest:<user_id>`.
- HTTP request sang AI phải có internal API key và correlation ID.

Kết quả: 10/10 response thành công; phiên A nhớ được thông tin từ lượt đầu đến lượt 7, phiên B không rò dữ liệu sang phiên A và ngược lại; replay trả cùng response, không ghi thêm message vào trạng thái. Chuỗi `turn_sequence` quan sát được là `1..7, 7` cho phiên A và `1, 2` cho phiên B.

HTTP boundary phía AI trong bài Backend là stateful mock để phép thử ổn định và cô lập. Hành vi memory thật của FastAPI được đối chứng riêng bằng bốn integration test: phiên 7 lượt có sửa sở thích, idempotency đồng thời, từ chối lượt sai thứ tự và compaction có giới hạn.

## Lệnh tái hiện

```powershell
cd service-api-ecommerce
.\mvnw.cmd '-Dtest=AiAssistantGatewayLongMemoryTest,AiAssistantControllerTest,AiAssistantChatServiceImplTest,RestAiServiceClientTest' test
```

Kết quả: `Tests run: 12, Failures: 0, Errors: 0, Skipped: 0`.

```powershell
cd service-ai
.\.venv\Scripts\python.exe -m pytest `
  tests/integration/test_assistant_chat.py::test_assistant_chat_keeps_mixed_preferences_and_corrects_same_session `
  tests/integration/test_assistant_chat.py::test_assistant_chat_is_idempotent_and_serializes_same_thread_requests `
  tests/integration/test_assistant_chat.py::test_assistant_chat_rejects_out_of_order_turn_sequence `
  tests/integration/test_assistant_chat.py::test_assistant_forces_compaction_and_passes_structured_state_to_llm -q
```

Kết quả: `4 passed`.

## Kết luận

Giới hạn “chỉ đạt trên endpoint AI” được gỡ ở mức kiểm thử contract xuyên Backend gateway và integration test phía AI. Phép thử này chưa thay thế smoke test trên một deployment thật chạy đồng thời cả hai tiến trình.
