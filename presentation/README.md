# Slide đồ án tốt nghiệp

Thư mục này chứa bộ slide được sinh tự động cho đề tài:

> Xây dựng Trợ lý Mua sắm Đa phương tiện sử dụng RAG và Computer Vision

## Nội dung hiện tại

- `DoAnTotNghiep.pptx` và `DoAnTotNghiep.pdf`: bản hoàn chỉnh gồm 32 slide chính và 6 slide phụ lục A1–A6.
- `scripts/build-presentation.ps1`: mã nguồn tái tạo toàn bộ file PowerPoint hoàn chỉnh.
- `notes/`: lời dẫn cho slide 1–32, kịch bản demo và cách dùng phụ lục.
- `assets/video/`: vị trí đặt video để script tự động nhúng vào slide 21.
- `previews/final/`: 38 ảnh slide và contact sheet toàn bộ.
- `previews/sections/`: contact sheet theo từng phần trình bày.
- `previews/reference/`: ảnh tham khảo dùng trong quá trình thiết kế.
- `archive/versions/`: các bản trung gian 8, 16 và 21 slide.

## Cấu trúc thư mục

```text
presentation/
├── DoAnTotNghiep.pptx
├── README.md
├── archive/versions/
├── assets/video/
├── notes/
├── previews/
│   ├── final/
│   ├── sections/
│   └── reference/
└── scripts/build-presentation.ps1
```

## Tái tạo file PPTX

Yêu cầu Microsoft PowerPoint trên Windows. Từ thư mục gốc project, chạy:

```powershell
powershell -ExecutionPolicy Bypass -File presentation/scripts/build-presentation.ps1
```

Script sử dụng ảnh, sơ đồ và số liệu kiểm thử thật trong project, sau đó ghi đè file PPTX, PDF cùng 38 ảnh preview. Nếu có `assets/video/demo-san-pham.mp4`, video sẽ được nhúng vào slide 21 và nút mở file dự phòng sẽ được tạo bằng đường dẫn tương đối.

## Quy ước thiết kế

- Tỷ lệ 16:9, kích thước widescreen.
- Font Aptos/Aptos Display để tương thích PowerPoint hiện đại.
- Màu chủ đạo xanh navy, xanh ngọc; cam dùng cho điểm nhấn/cảnh báo.
- Mỗi slide giữ một thông điệp chính, ưu tiên sơ đồ và cụm từ ngắn.
- Phần trình bày chính gồm 32 slide; slide 31 là Q&A, slide 32 là tài liệu tham khảo; 6 trang sau được đánh số A1–A6 và chỉ dùng khi hỏi đáp sâu.
