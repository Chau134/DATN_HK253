# HCMUT Software Engineering Report Template

Template LaTeX cho báo cáo đồ án Công nghệ phần mềm, đã map theo mục lục yêu cầu.

## Cách compile

Trên Overleaf:

1. Upload toàn bộ file zip.
2. Mở `main.tex`.
3. Chọn compiler `pdfLaTeX`.
4. Bibliography dùng `Biber`.
5. Compile theo chu trình: pdfLaTeX → Biber → pdfLaTeX → pdfLaTeX.

## File cần sửa nhiều nhất

- `Preamble/metadata.tex`: thông tin bìa, tên đề tài, GVHD, sinh viên.
- `FrontMatter/summary_vi.tex`: tóm tắt tiếng Việt.
- `FrontMatter/abstract_en.tex`: abstract tiếng Anh.
- `FrontMatter/abbreviations.tex`: danh mục từ viết tắt.
- `Sections/*.tex`: nội dung từng chương.
- `References/refs.bib`: tài liệu tham khảo.

## Mục lục đã map

- Tóm tắt báo cáo
- Abstract
- Mục lục
- Danh mục từ viết tắt
- Danh mục hình
- Danh mục bảng
- Guideline -- Hướng dẫn viết báo cáo và LaTeX
- Chương 1 -- Giới thiệu
- Chương 2 -- Kiến thức nền tảng
- Chương 3 -- Công nghệ và quyết định lựa chọn
- Chương 4 -- Khai thác yêu cầu
- Chương 5 -- Phân tích hệ thống
- Chương 6 -- Thiết kế hệ thống
- Chương 7 -- Cài đặt hệ thống
- Chương 8 -- Hiện thực hệ thống
- Chương 9 -- Đánh giá hệ thống
- Chương 10 -- Kết luận và hướng phát triển
- Kế hoạch thực hiện Đồ án tốt nghiệp
- Tài liệu tham khảo

## Khi nộp bản chính thức

Comment dòng guideline trong `main.tex`:

```tex
% \input{Sections/00-Guideline}
```

## Quy tắc citation

Từ Chương 1 đến hết báo cáo, phần nào lấy ý tưởng, dữ liệu, nhận định, định nghĩa hoặc mô tả từ tài liệu khác thì phải trích dẫn trực tiếp tại đoạn đó bằng `\parencite{key}` hoặc `\textcite{key}`.
