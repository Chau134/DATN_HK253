$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$posterDir = Split-Path -Parent $scriptDir
$workspaceDir = Split-Path -Parent $posterDir
$outputPptx = Join-Path $posterDir 'HK253-DATN-071_poster-mau-A1.pptx'
$outputPdf = Join-Path $posterDir 'HK253-DATN-071_poster-mau-A1.pdf'
$previewPath = Join-Path $posterDir 'HK253-DATN-071_poster-mau-A1.png'

function Pt([double]$inch) { $inch * 72.0 }
function Rgb([int]$r, [int]$g, [int]$b) { $r + ($g * 256) + ($b * 65536) }

$C = @{
    Navy = Rgb 7 24 43
    Navy2 = Rgb 12 39 64
    Card = Rgb 19 51 78
    White = Rgb 248 251 253
    Ink = Rgb 20 34 49
    Muted = Rgb 177 197 211
    Teal = Rgb 37 210 187
    Blue = Rgb 52 126 255
    Orange = Rgb 255 157 79
    Red = Rgb 243 91 110
    Light = Rgb 236 244 248
    DarkTeal = Rgb 12 131 126
    Line = Rgb 55 87 112
}

$msoFalse = 0
$msoTrue = -1
$msoTextOrientationHorizontal = 1
$msoShapeRectangle = 1
$msoShapeRoundedRectangle = 5
$msoShapeOval = 9
$ppLayoutBlank = 12
$ppSaveAsOpenXMLPresentation = 24
$ppSaveAsPDF = 32

function Add-Shape {
    param($slide, [int]$type, [double]$x, [double]$y, [double]$w, [double]$h,
          [int]$fill, [int]$line = -1, [double]$transparency = 0)
    $shape = $slide.Shapes.AddShape($type, (Pt $x), (Pt $y), (Pt $w), (Pt $h))
    $shape.Fill.ForeColor.RGB = $fill
    $shape.Fill.Transparency = $(if ($transparency -gt 1) { $transparency / 100.0 } else { $transparency })
    if ($line -lt 0) {
        $shape.Line.Visible = $msoFalse
    } else {
        $shape.Line.Visible = $msoTrue
        $shape.Line.ForeColor.RGB = $line
        $shape.Line.Weight = 1.2
    }
    $shape
}

function Add-Text {
    param($slide, [string]$text, [double]$x, [double]$y, [double]$w, [double]$h,
          [double]$size, [int]$color, [bool]$bold = $false, [int]$align = 1,
          [string]$font = 'Aptos', [int]$vertical = 1, [double]$margin = 0.05)
    $box = $slide.Shapes.AddTextbox($msoTextOrientationHorizontal, (Pt $x), (Pt $y), (Pt $w), (Pt $h))
    $box.TextFrame2.MarginLeft = Pt $margin
    $box.TextFrame2.MarginRight = Pt $margin
    $box.TextFrame2.MarginTop = Pt $margin
    $box.TextFrame2.MarginBottom = Pt $margin
    $box.TextFrame2.WordWrap = $msoTrue
    $box.TextFrame2.AutoSize = 2
    $box.TextFrame2.VerticalAnchor = $vertical
    $range = $box.TextFrame2.TextRange
    $range.Text = $text
    $range.Font.Name = $font
    $range.Font.Size = $size
    $range.Font.Fill.ForeColor.RGB = $color
    $range.Font.Bold = $(if ($bold) { $msoTrue } else { $msoFalse })
    $range.ParagraphFormat.Alignment = $align
    $box
}

function Add-Line {
    param($slide, [double]$x1, [double]$y1, [double]$x2, [double]$y2, [int]$color, [double]$weight = 2)
    $line = $slide.Shapes.AddLine((Pt $x1), (Pt $y1), (Pt $x2), (Pt $y2))
    $line.Line.ForeColor.RGB = $color
    $line.Line.Weight = $weight
    $line
}

function Add-PictureContain {
    param($slide, [string]$path, [double]$x, [double]$y, [double]$w, [double]$h)
    $pic = $slide.Shapes.AddPicture($path, $msoFalse, $msoTrue, (Pt $x), (Pt $y), -1, -1)
    $sourceRatio = $pic.Width / $pic.Height
    $targetRatio = $w / $h
    if ($sourceRatio -gt $targetRatio) {
        $pic.Width = Pt $w
        $pic.Height = $pic.Width / $sourceRatio
    } else {
        $pic.Height = Pt $h
        $pic.Width = $pic.Height * $sourceRatio
    }
    $pic.Left = Pt ($x + (($w - ($pic.Width / 72.0)) / 2))
    $pic.Top = Pt ($y + (($h - ($pic.Height / 72.0)) / 2))
    $pic
}

function Add-SectionTitle {
    param($slide, [string]$index, [string]$title, [double]$x, [double]$y, [double]$w, [int]$accent)
    Add-Shape $slide $msoShapeRoundedRectangle $x $y 0.58 0.58 $accent | Out-Null
    Add-Text $slide $index $x $y 0.58 0.58 18 $C.Navy $true 2 'Aptos Display' 3 0 | Out-Null
    Add-Text $slide $title ($x + 0.78) ($y + 0.01) ($w - 0.78) 0.56 25 $C.White $true 1 'Aptos Display' 3 0 | Out-Null
}

function Add-ProblemCard {
    param($slide, [string]$index, [string]$title, [string]$body, [double]$y, [int]$accent)
    Add-Shape $slide $msoShapeRoundedRectangle 0.95 $y 6.45 2.12 $C.Card $C.Line | Out-Null
    Add-Shape $slide $msoShapeOval 1.25 ($y + 0.52) 0.76 0.76 $accent | Out-Null
    Add-Text $slide $index 1.25 ($y + 0.52) 0.76 0.76 20 $C.Navy $true 2 'Aptos Display' 3 0 | Out-Null
    Add-Text $slide $title 2.25 ($y + 0.38) 4.65 0.50 22 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $slide $body 2.25 ($y + 0.94) 4.65 0.78 17 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
}

function Add-MetricCard {
    param($slide, [string]$value, [string]$label, [string]$note, [double]$x, [double]$y, [int]$accent)
    Add-Shape $slide $msoShapeRoundedRectangle $x $y 3.18 2.15 $C.Card $accent | Out-Null
    Add-Text $slide $value ($x + 0.22) ($y + 0.24) 2.74 0.66 29 $accent $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $slide $label ($x + 0.22) ($y + 0.95) 2.74 0.42 17 $C.White $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $slide $note ($x + 0.22) ($y + 1.40) 2.74 0.50 12 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
}

$logoPath = Join-Path $workspaceDir 'report-datn\Images\hcmut.png'
$architecturePath = Join-Path $workspaceDir 'report-datn\Images\Thietkehethong\Kiến trúc tổng thể của hệ thống.drawio.drawio.png'
$searchPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện trợ lý mua sắm đa phương tiện.png'
$chatPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện chatbot.png'

New-Item -ItemType Directory -Force -Path $posterDir | Out-Null

$powerPoint = New-Object -ComObject PowerPoint.Application
$powerPoint.Visible = $msoTrue
$deck = $powerPoint.Presentations.Add()
$deck.PageSetup.SlideWidth = Pt 23.39
$deck.PageSetup.SlideHeight = Pt 33.11

try {
    $s = $deck.Slides.Add(1, $ppLayoutBlank)

    # Background and quiet visual accents.
    Add-Shape $s $msoShapeRectangle 0 0 23.39 33.11 $C.Navy | Out-Null
    Add-Shape $s $msoShapeOval 18.3 -3.0 9.0 9.0 $C.Blue -1 72 | Out-Null
    Add-Shape $s $msoShapeOval -3.3 27.8 8.0 8.0 $C.Teal -1 88 | Out-Null

    # Header.
    Add-PictureContain $s $logoPath 0.85 0.65 1.65 1.65 | Out-Null
    Add-Text $s "ĐẠI HỌC QUỐC GIA TP.HCM`rTRƯỜNG ĐẠI HỌC BÁCH KHOA`rKHOA KHOA HỌC VÀ KỸ THUẬT MÁY TÍNH" 2.78 0.73 9.6 1.34 17 $C.White $true 1 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 17.70 0.82 4.60 0.70 $C.Card $C.Teal | Out-Null
    Add-Text $s 'ĐỒ ÁN TỐT NGHIỆP · HK253' 17.90 1.00 4.20 0.31 15 $C.Teal $true 2 'Aptos' 1 0 | Out-Null
    Add-Line $s 0.88 2.55 22.51 2.55 $C.Line 1.5 | Out-Null

    Add-Text $s 'XÂY DỰNG TRỢ LÝ MUA SẮM' 0.90 3.03 21.59 0.86 44 $C.White $true 2 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'ĐA PHƯƠNG TIỆN SỬ DỤNG RAG VÀ COMPUTER VISION' 0.90 3.93 21.59 0.92 34 $C.Teal $true 2 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'HK253-DATN-071  ·  Tìm kiếm bằng văn bản, hình ảnh và hội thoại trong một hành trình mua sắm xuyên suốt' 1.45 5.05 20.49 0.54 18 $C.Muted $false 2 'Aptos' 1 0 | Out-Null
    Add-Text $s 'GVHD: ThS. Võ Thanh Hùng' 1.10 5.82 6.20 0.42 17 $C.White $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'SVTH: Lê Trần Anh Dũng · 2210576   |   Huỳnh Thái Minh Châu · 2210352   |   Nguyễn Đức Duy · 2210510' 7.05 5.82 15.20 0.42 15 $C.White $false 3 'Aptos' 1 0 | Out-Null

    # Problem column.
    Add-SectionTitle $s '01' 'VẤN ĐỀ GIẢI QUYẾT' 0.88 6.75 6.80 $C.Orange
    Add-ProblemCard $s 'A' 'Khoảng cách ngữ nghĩa' 'Người mua biết nhu cầu nhưng không nhớ đúng tên hoặc từ khóa sản phẩm.' 7.62 $C.Blue
    Add-ProblemCard $s 'B' 'Khoảng cách thị giác' 'Người mua có ảnh tham khảo nhưng khó diễn tả chính xác kiểu dáng bằng lời.' 9.98 $C.Orange
    Add-ProblemCard $s 'C' 'Mất ngữ cảnh hội thoại' 'Các câu hỏi nối tiếp về màu, size, giá dễ bị hiểu sai nếu xử lý độc lập.' 12.34 $C.Teal
    Add-Shape $s $msoShapeRoundedRectangle 0.95 14.83 6.45 1.64 $C.Navy2 $C.Orange | Out-Null
    Add-Text $s 'MỤC TIÊU' 1.24 15.10 1.45 0.33 14 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Hiểu đồng thời văn bản, hình ảnh và lịch sử trao đổi để giúp người dùng tìm đúng và quyết định nhanh hơn.' 1.24 15.54 5.82 0.62 17 $C.White $true 1 'Aptos' 1 0 | Out-Null

    # Solution area.
    Add-SectionTitle $s '02' 'GIẢI PHÁP ĐỀ XUẤT' 8.05 6.75 14.42 $C.Teal
    $steps = @(
        @('Văn bản + ảnh', $C.Blue),
        @('Hiểu ý định', $C.Orange),
        @('Truy hồi vector', $C.Teal),
        @('RAG + bộ nhớ', $C.Blue),
        @('Xác nhận nghiệp vụ', $C.Red)
    )
    $stepX = 8.08
    for ($i = 0; $i -lt $steps.Count; $i++) {
        Add-Shape $s $msoShapeRoundedRectangle $stepX 7.65 2.48 1.12 $C.Card $steps[$i][1] | Out-Null
        Add-Text $s ('0' + ($i + 1)) ($stepX + 0.12) 7.82 0.40 0.28 12 $steps[$i][1] $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $steps[$i][0] ($stepX + 0.12) 8.13 2.22 0.38 14 $C.White $true 1 'Aptos' 1 0 | Out-Null
        if ($i -lt ($steps.Count - 1)) {
            Add-Text $s '›' ($stepX + 2.50) 7.84 0.42 0.52 27 $C.Muted $true 2 'Aptos Display' 1 0 | Out-Null
        }
        $stepX += 2.86
    }
    Add-Shape $s $msoShapeRoundedRectangle 8.05 9.18 14.42 7.29 $C.White | Out-Null
    Add-PictureContain $s $architecturePath 8.40 9.54 13.72 5.70 | Out-Null
    Add-Text $s 'Kiến trúc tách biệt trách nhiệm: Spring Boot giữ nghiệp vụ và dữ liệu hiện hành; FastAPI điều phối AI; Qdrant phục vụ truy hồi; checkpoint duy trì ngữ cảnh.' 8.48 15.35 13.56 0.72 16 $C.Ink $true 2 'Aptos' 1 0 | Out-Null

    # Product evidence.
    Add-SectionTitle $s '03' 'SẢN PHẨM HOÀN CHỈNH' 0.88 17.17 14.62 $C.Blue
    Add-Shape $s $msoShapeRoundedRectangle 0.95 18.07 14.55 7.75 $C.White | Out-Null
    Add-PictureContain $s $searchPath 1.25 18.37 13.95 6.28 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 1.28 24.82 3.95 0.64 $C.Blue | Out-Null
    Add-Text $s 'TEXT SEARCH' 1.28 24.98 3.95 0.28 13 $C.White $true 2 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 5.57 24.82 3.95 0.64 $C.Orange | Out-Null
    Add-Text $s 'IMAGE SEARCH' 5.57 24.98 3.95 0.28 13 $C.Navy $true 2 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 9.86 24.82 4.88 0.64 $C.Teal | Out-Null
    Add-Text $s 'HYBRID SEARCH' 9.86 24.98 4.88 0.28 13 $C.Navy $true 2 'Aptos' 1 0 | Out-Null

    # Results.
    Add-SectionTitle $s '04' 'KẾT QUẢ NỔI BẬT' 15.88 17.17 6.59 $C.Teal
    Add-MetricCard $s '1,000' 'Text Search' 'Hit@5 · tập đánh giá 1.000 sản phẩm' 15.88 18.07 $C.Blue
    Add-MetricCard $s '0,970' 'Image Search' 'Exact Hit@5 · tập ảnh challenging' 19.29 18.07 $C.Orange
    Add-MetricCard $s '0,920' 'Hybrid Search' 'Strict Hit@5 · fusion không rerank' 15.88 20.48 $C.Teal
    Add-MetricCard $s '1,000' 'RAG grounding' 'Context Precision 0,946 · Recall 0,944' 19.29 20.48 $C.Blue
    Add-MetricCard $s '102/102' 'Backend đạt' 'Ca kiểm thử chức năng' 15.88 22.89 $C.Orange
    Add-MetricCard $s '430/430' 'AI hồi quy đạt' 'Bộ kiểm thử regression' 19.29 22.89 $C.Teal

    # Conversation / end-to-end strip.
    Add-SectionTitle $s '05' 'TỪ TƯ VẤN ĐẾN HÀNH ĐỘNG MUA HÀNG' 0.88 26.46 21.59 $C.Orange
    Add-Shape $s $msoShapeRoundedRectangle 0.95 27.36 12.80 3.38 $C.White | Out-Null
    Add-PictureContain $s $chatPath 1.22 27.62 12.26 2.86 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 14.10 27.36 8.37 3.38 $C.Navy2 $C.Teal | Out-Null
    Add-Text $s 'ĐÓNG GÓP CHÍNH' 14.50 27.76 3.15 0.35 15 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s "• Tìm kiếm đa phương thức trong một giao diện`r• Tư vấn RAG có căn cứ và bộ nhớ nhiều lượt`r• Tích hợp trực tiếp giỏ hàng, đặt hàng và quản trị`r• Đánh giá bằng baseline, ablation và kiểm thử hệ thống" 14.48 28.22 7.55 1.80 16 $C.White $false 1 'Aptos' 1 0 | Out-Null

    # Closing statement and footer.
    Add-Shape $s $msoShapeRoundedRectangle 0.95 31.10 18.85 1.15 $C.Teal | Out-Null
    Add-Text $s 'AI hỗ trợ quyết định. Dữ liệu nghiệp vụ giữ quyền kiểm soát.' 1.35 31.39 18.05 0.46 24 $C.Navy $true 2 'Aptos Display' 3 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 20.08 31.10 2.39 1.15 $C.Card $C.Muted | Out-Null
    Add-Text $s 'QR DEMO' 20.08 31.28 2.39 0.30 14 $C.White $true 2 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Thay bằng mã QR' 20.08 31.67 2.39 0.24 10 $C.Muted $false 2 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Phạm vi thử nghiệm: snapshot 1.000 sản phẩm. Hybrid Search còn hạn chế khi phải thỏa đồng thời nhiều ràng buộc.' 1.02 32.48 17.80 0.28 11 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'React · Spring Boot · FastAPI · LangGraph · MySQL · Qdrant · Docker' 15.10 32.48 7.25 0.28 11 $C.Muted $false 3 'Aptos' 1 0 | Out-Null

    $deck.SaveAs($outputPptx, $ppSaveAsOpenXMLPresentation)
    $s.Export($previewPath, 'PNG', 1403, 1986)
    $deck.SaveAs($outputPdf, $ppSaveAsPDF)
}
finally {
    if ($deck) { $deck.Close() }
    if ($powerPoint) { $powerPoint.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($deck) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Write-Host "Created: $outputPptx"
Write-Host "Created: $outputPdf"
Write-Host "Created: $previewPath"
