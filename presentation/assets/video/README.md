# Video demo

Đặt video tại:

```text
presentation/assets/video/demo-san-pham.mp4
```

Sau đó chạy lại:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File presentation/scripts/build-presentation.ps1
```

Script sẽ tự động nhúng video vào slide 21 của `DoAnTotNghiep_21slides.pptx`. Nếu chưa có video, slide sử dụng thumbnail giao diện và nút phát minh họa.

Định dạng khuyến nghị: MP4, H.264 video, AAC audio, 1920×1080, 30 fps. Nên giữ video trong khoảng 3–4 phút để tránh chiếm quá nhiều thời gian bảo vệ.
