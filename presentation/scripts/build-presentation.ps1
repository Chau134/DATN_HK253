$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$presentationDir = Split-Path -Parent $scriptDir
$workspaceDir = Split-Path -Parent $presentationDir
$outputPath = Join-Path $presentationDir 'DoAnTotNghiep.pptx'
if (-not [string]::IsNullOrWhiteSpace($env:DATN_PRESENTATION_OUTPUT)) {
    $outputPath = [System.IO.Path]::GetFullPath($env:DATN_PRESENTATION_OUTPUT)
}
$pdfPath = [System.IO.Path]::ChangeExtension($outputPath, '.pdf')
$previewDir = Join-Path $presentationDir 'previews\final'

New-Item -ItemType Directory -Force -Path $previewDir | Out-Null

function Pt([double]$inch) { return $inch * 72.0 }
function Rgb([int]$r, [int]$g, [int]$b) { return $r + ($g * 256) + ($b * 65536) }

$C = @{
    Navy       = Rgb 8 22 40
    Navy2      = Rgb 13 35 58
    Ink        = Rgb 22 31 45
    White      = Rgb 247 250 252
    Muted      = Rgb 173 192 207
    Teal       = Rgb 39 207 185
    TealDark   = Rgb 13 129 125
    Blue       = Rgb 51 124 255
    Orange     = Rgb 255 151 74
    Red        = Rgb 245 93 105
    Card       = Rgb 20 45 70
    CardLight  = Rgb 237 244 248
    Line       = Rgb 62 92 118
    DarkLine   = Rgb 29 55 79
    Gray       = Rgb 91 111 128
}

$ppLayoutBlank = 12
$ppSaveAsOpenXMLPresentation = 24
$ppSaveAsPDF = 32
$msoTextOrientationHorizontal = 1
$msoShapeRectangle = 1
$msoShapeRoundedRectangle = 5
$msoShapeOval = 9
$msoFalse = 0
$msoTrue = -1
$mainSlideCount = 32

function Add-Shape {
    param($slide, [int]$type, [double]$x, [double]$y, [double]$w, [double]$h,
          [int]$fill, [int]$line = -1, [double]$radius = 0, [double]$transparency = 0)
    $shape = $slide.Shapes.AddShape($type, (Pt $x), (Pt $y), (Pt $w), (Pt $h))
    $shape.Fill.ForeColor.RGB = $fill
    $shape.Fill.Transparency = $(if ($transparency -gt 1) { $transparency / 100.0 } else { $transparency })
    if ($line -lt 0) {
        $shape.Line.Visible = $msoFalse
    } else {
        $shape.Line.Visible = $msoTrue
        $shape.Line.ForeColor.RGB = $line
        $shape.Line.Weight = 1
    }
    return $shape
}

function Add-Line {
    param($slide, [double]$x1, [double]$y1, [double]$x2, [double]$y2,
          [int]$color, [double]$weight = 1.5, [double]$transparency = 0)
    $line = $slide.Shapes.AddLine((Pt $x1), (Pt $y1), (Pt $x2), (Pt $y2))
    $line.Line.ForeColor.RGB = $color
    $line.Line.Weight = $weight
    $line.Line.Transparency = $transparency
    return $line
}

function Add-Text {
    param($slide, [string]$text, [double]$x, [double]$y, [double]$w, [double]$h,
          [double]$size = 20, [int]$color = 0, [bool]$bold = $false,
          [int]$align = 1, [string]$font = 'Aptos', [int]$vertical = 1,
          [double]$margin = 0.02)
    $box = $slide.Shapes.AddTextbox($msoTextOrientationHorizontal, (Pt $x), (Pt $y), (Pt $w), (Pt $h))
    $box.TextFrame2.MarginLeft = Pt $margin
    $box.TextFrame2.MarginRight = Pt $margin
    $box.TextFrame2.MarginTop = Pt $margin
    $box.TextFrame2.MarginBottom = Pt $margin
    $box.TextFrame2.WordWrap = $msoTrue
    # Tăng khả năng đọc trên màn chiếu; PowerPoint chỉ thu nhỏ khi nội dung thật sự vượt khung.
    $box.TextFrame2.AutoSize = 2
    $box.TextFrame2.VerticalAnchor = $vertical
    $range = $box.TextFrame2.TextRange
    $range.Text = $text
    $range.Font.Name = $font
    $range.Font.Size = $size + 2
    $range.Font.Fill.ForeColor.RGB = $color
    $range.Font.Bold = $(if ($bold) { $msoTrue } else { $msoFalse })
    $range.ParagraphFormat.Alignment = $align
    return $box
}

function Add-RichText {
    param($slide, [string]$prefix, [string]$main, [double]$x, [double]$y, [double]$w, [double]$h,
          [double]$prefixSize, [double]$mainSize, [int]$prefixColor, [int]$mainColor)
    $text = "$prefix`r$main"
    $box = Add-Text $slide $text $x $y $w $h $mainSize $mainColor $true 1 'Aptos Display' 1 0
    $r1 = $box.TextFrame2.TextRange.Paragraphs(1)
    $r1.Font.Size = $prefixSize + 2
    $r1.Font.Fill.ForeColor.RGB = $prefixColor
    $r1.Font.Bold = $msoTrue
    $r2 = $box.TextFrame2.TextRange.Paragraphs(2)
    $r2.Font.Size = $mainSize + 2
    $r2.Font.Fill.ForeColor.RGB = $mainColor
    $r2.Font.Bold = $msoTrue
    return $box
}

function Add-PictureFit {
    param($slide, [string]$path, [double]$x, [double]$y, [double]$w, [double]$h)
    $shape = $slide.Shapes.AddPicture($path, $msoFalse, $msoTrue, (Pt $x), (Pt $y), -1, -1)
    $sourceRatio = $shape.Width / $shape.Height
    $targetRatio = $w / $h
    if ($sourceRatio -gt $targetRatio) {
        $shape.Height = Pt $h
        $shape.Width = $shape.Height * $sourceRatio
    } else {
        $shape.Width = Pt $w
        $shape.Height = $shape.Width / $sourceRatio
    }
    $shape.Left = Pt ($x + (($w - ($shape.Width / 72.0)) / 2.0))
    $shape.Top = Pt ($y + (($h - ($shape.Height / 72.0)) / 2.0))
    return $shape
}

function Add-PictureContain {
    param($slide, [string]$path, [double]$x, [double]$y, [double]$w, [double]$h)
    $shape = $slide.Shapes.AddPicture($path, $msoFalse, $msoTrue, (Pt $x), (Pt $y), -1, -1)
    $sourceRatio = $shape.Width / $shape.Height
    $targetRatio = $w / $h
    if ($sourceRatio -gt $targetRatio) {
        $shape.Width = Pt $w
        $shape.Height = $shape.Width / $sourceRatio
    } else {
        $shape.Height = Pt $h
        $shape.Width = $shape.Height * $sourceRatio
    }
    $shape.Left = Pt ($x + (($w - ($shape.Width / 72.0)) / 2.0))
    $shape.Top = Pt ($y + (($h - ($shape.Height / 72.0)) / 2.0))
    return $shape
}

function Add-CircleLabel {
    param($slide, [string]$text, [double]$x, [double]$y, [double]$diameter,
          [int]$fill, [int]$textColor, [double]$size = 18)
    Add-Shape $slide $msoShapeOval $x $y $diameter $diameter $fill | Out-Null
    Add-Text $slide $text $x $y $diameter $diameter $size $textColor $true 2 'Aptos Display' 3 0 | Out-Null
}

function Add-Title {
    param($slide, [string]$kicker, [string]$title, [string]$subtitle = '')
    Add-Text $slide $kicker.ToUpperInvariant() 0.65 0.32 4.2 0.27 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $slide $title 0.65 0.68 12.0 0.66 28 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    if ($subtitle) {
        Add-Text $slide $subtitle 0.68 1.32 11.7 0.42 13 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
}

function Add-Footer {
    param($slide, [int]$number, [string]$section = 'MỞ ĐẦU & BÀI TOÁN')
    Add-Line $slide 0.65 7.15 12.68 7.15 $C.DarkLine 0.8 | Out-Null
    Add-Text $slide $section 0.67 7.20 3.0 0.16 8 $C.Gray $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $slide ("{0:D2} / {1}" -f $number, $mainSlideCount) 11.30 7.18 1.35 0.18 8 $C.Gray $true 3 'Aptos' 1 0 | Out-Null
}

function Add-AppendixFooter {
    param($slide, [string]$label)
    Add-Line $slide 0.65 7.15 12.68 7.15 $C.DarkLine 0.8 | Out-Null
    Add-Text $slide 'PHỤ LỤC · DÙNG KHI HỎI ĐÁP' 0.67 7.20 3.3 0.16 8 $C.Gray $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $slide $label 11.30 7.18 1.35 0.18 8 $C.Gray $true 3 'Aptos' 1 0 | Out-Null
}

function Add-Background {
    param($slide)
    $bg = Add-Shape $slide $msoShapeRectangle 0 0 13.333 7.5 $C.Navy
    $bg.ZOrder(1)
    Add-Shape $slide $msoShapeOval 10.7 -1.7 4.3 4.3 $C.Blue -1 0 78 | Out-Null
    Add-Shape $slide $msoShapeOval -1.2 5.7 3.2 3.2 $C.Teal -1 0 90 | Out-Null
}

function Add-IconSearch {
    param($slide, [double]$x, [double]$y, [int]$color)
    $circle = Add-Shape $slide $msoShapeOval $x $y 0.35 0.35 $C.Navy $color
    $circle.Fill.Transparency = 1
    $circle.Line.Weight = 2.3
    Add-Line $slide ($x + 0.27) ($y + 0.27) ($x + 0.48) ($y + 0.48) $color 2.3 | Out-Null
}

function Add-IconImage {
    param($slide, [double]$x, [double]$y, [int]$color)
    $frame = Add-Shape $slide $msoShapeRoundedRectangle $x $y 0.55 0.45 $C.Navy $color
    $frame.Fill.Transparency = 1
    $frame.Line.Weight = 2
    Add-Shape $slide $msoShapeOval ($x + 0.34) ($y + 0.08) 0.08 0.08 $color | Out-Null
    Add-Line $slide ($x + 0.08) ($y + 0.35) ($x + 0.22) ($y + 0.22) $color 1.6 | Out-Null
    Add-Line $slide ($x + 0.22) ($y + 0.22) ($x + 0.32) ($y + 0.31) $color 1.6 | Out-Null
    Add-Line $slide ($x + 0.32) ($y + 0.31) ($x + 0.45) ($y + 0.17) $color 1.6 | Out-Null
}

function Add-IconChat {
    param($slide, [double]$x, [double]$y, [int]$color)
    $bubble = Add-Shape $slide $msoShapeRoundedRectangle $x $y 0.58 0.40 $C.Navy $color
    $bubble.Fill.Transparency = 1
    $bubble.Line.Weight = 2
    Add-Line $slide ($x + 0.14) ($y + 0.15) ($x + 0.43) ($y + 0.15) $color 1.5 | Out-Null
    Add-Line $slide ($x + 0.14) ($y + 0.25) ($x + 0.34) ($y + 0.25) $color 1.5 | Out-Null
}

$logoPath = Join-Path $workspaceDir 'report-datn\Images\hcmut.png'
$homePath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện trang chủ của hệ thống.png'
$assistantPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện trợ lý mua sắm đa phương tiện.png'
$catalogPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện danh mục, tìm kiếm và lọc sản phẩm.png'
$architecturePath = Join-Path $workspaceDir 'report-datn\Images\Thietkehethong\Kiến trúc tổng thể của hệ thống.drawio.drawio.png'
$chatbotPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện chatbot.png'
$detailPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện chi tiết sản phẩm.png'
$cartPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện quản lý giỏ hàng.png'
$checkoutPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện thanh toán.png'
$adminPath = Join-Path $workspaceDir 'report-datn\Images\Frontend\giao diện tổng quan dành cho quản trị viên.png'
$videoPath = Join-Path $presentationDir 'assets\video\demo-san-pham.mp4'

$powerPoint = New-Object -ComObject PowerPoint.Application
$powerPoint.Visible = $msoTrue
$deck = $powerPoint.Presentations.Add()
$deck.PageSetup.SlideWidth = Pt 13.333
$deck.PageSetup.SlideHeight = Pt 7.5

try {
    # 01 — Cover
    $s = $deck.Slides.Add(1, $ppLayoutBlank)
    Add-Background $s
    Add-PictureContain $s $logoPath 0.70 0.38 0.72 0.72 | Out-Null
    Add-Text $s "ĐẠI HỌC QUỐC GIA TP. HỒ CHÍ MINH`rTRƯỜNG ĐẠI HỌC BÁCH KHOA · KHOA KH&KT MÁY TÍNH" 1.58 0.40 6.20 0.64 9 $C.White $true 1 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 9.84 0.46 2.79 0.48 $C.Card $C.Teal | Out-Null
    Add-Text $s 'TP. HỒ CHÍ MINH · 09/2026' 10.04 0.60 2.39 0.19 9 $C.Teal $true 2 'Aptos' 1 0 | Out-Null
    Add-Line $s 0.70 1.23 12.63 1.23 $C.Line 1.1 | Out-Null

    Add-Text $s 'ĐỒ ÁN TỐT NGHIỆP  ·  KHOA HỌC MÁY TÍNH' 0.72 1.58 6.70 0.24 10 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'XÂY DỰNG TRỢ LÝ' 0.68 2.00 7.20 0.52 27 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'MUA SẮM ĐA PHƯƠNG TIỆN' 0.68 2.52 7.52 0.64 31 $C.Teal $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'SỬ DỤNG RAG VÀ COMPUTER VISION' 0.72 3.20 7.20 0.40 18 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Line $s 0.72 3.82 1.82 3.82 $C.Teal 3 | Out-Null
    Add-Text $s 'Tìm kiếm bằng văn bản, hình ảnh và hội thoại — gắn kết trực tiếp với dữ liệu và hành trình mua sắm.' 0.72 4.08 6.95 0.72 14 $C.Muted $false 1 'Aptos' 1 0 | Out-Null

    Add-Shape $s $msoShapeRoundedRectangle 8.28 1.54 4.35 3.93 $C.Card $C.Line | Out-Null
    Add-Text $s 'MULTIMODAL SHOPPING ASSISTANT' 8.62 1.87 3.66 0.22 10 $C.Teal $true 2 'Aptos' 1 0 | Out-Null
    $coverInputs=@(
        @{Y=2.40;N='T';T='Văn bản';C=$C.Blue},
        @{Y=3.18;N='I';T='Hình ảnh';C=$C.Orange},
        @{Y=3.96;N='C';T='Hội thoại';C=$C.Teal}
    )
    foreach($input in $coverInputs){
        Add-Shape $s $msoShapeRoundedRectangle 8.62 $input.Y 1.50 0.57 $C.Navy2 $C.Line | Out-Null
        Add-CircleLabel $s $input.N 8.80 ($input.Y+0.11) 0.34 $input.C $C.Navy 9
        Add-Text $s $input.T 9.27 ($input.Y+0.15) 0.70 0.22 10 $C.White $true 1 'Aptos' 1 0 | Out-Null
        Add-Line $s 10.12 ($input.Y+0.29) 10.67 3.51 $input.C 1.3 0.2 | Out-Null
    }
    Add-CircleLabel $s 'AI' 10.67 3.02 1.00 $C.Teal $C.Navy 21
    Add-Line $s 11.17 4.02 11.17 4.43 $C.Teal 1.8 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 9.86 4.43 2.62 0.68 $C.Navy2 $C.Teal | Out-Null
    Add-Text $s 'RAG  ·  VECTOR  ·  MEMORY' 10.04 4.56 2.26 0.20 9 $C.Teal $true 2 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Gợi ý có căn cứ' 10.04 4.80 2.26 0.20 10 $C.White $true 2 'Aptos Display' 1 0 | Out-Null

    Add-Shape $s $msoShapeRoundedRectangle 0.70 5.58 11.93 1.10 $C.Navy2 $C.Line | Out-Null
    Add-CircleLabel $s 'MC' 0.95 5.85 0.54 $C.Teal $C.Navy 11
    Add-Text $s 'HUỲNH THÁI MINH CHÂU' 1.65 5.77 2.76 0.28 13 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'MSSV 2210352' 1.65 6.12 1.84 0.20 9 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 4.55 5.78 4.55 6.49 $C.Line 1 | Out-Null
    Add-Text $s 'GVHD' 4.84 5.76 0.72 0.20 9 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'ThS. Võ Thanh Hùng' 4.84 6.08 2.18 0.26 11 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Line $s 7.28 5.78 7.28 6.49 $C.Line 1 | Out-Null
    Add-Text $s 'GVPB' 7.57 5.76 0.72 0.20 9 $C.Red $true 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 7.57 6.35 9.34 6.35 $C.Line 1 | Out-Null
    Add-Line $s 9.63 5.78 9.63 6.49 $C.Line 1 | Out-Null
    Add-Text $s 'HỘI ĐỒNG' 9.92 5.76 1.20 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 9.92 6.35 12.18 6.35 $C.Line 1 | Out-Null
    Add-Text $s '01 / 32' 11.30 7.18 1.35 0.18 8 $C.Gray $true 3 'Aptos' 1 0 | Out-Null

    # 02 — Agenda
    $s = $deck.Slides.Add(2, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Lộ trình trình bày' 'Từ bài toán đến bằng chứng' '32 slide · 5 phần · một câu chuyện xuyên suốt'
    $chapters = @(
        @{No='01'; Name='Mở đầu & bài toán'; Range='01–08'; Active=$true},
        @{No='02'; Name='Phân tích & thiết kế'; Range='09–16'; Active=$false},
        @{No='03'; Name='Sản phẩm & demo'; Range='17–21'; Active=$false},
        @{No='04'; Name='Kiểm thử & đánh giá'; Range='22–28'; Active=$false},
        @{No='05'; Name='Kết luận & trao đổi'; Range='29–32'; Active=$false}
    )
    $x = 0.68
    for ($i=0; $i -lt $chapters.Count; $i++) {
        $ch = $chapters[$i]
        $fill = if ($ch.Active) { $C.Teal } else { $C.Card }
        $fg = if ($ch.Active) { $C.Navy } else { $C.White }
        $muted = if ($ch.Active) { $C.TealDark } else { $C.Muted }
        Add-Shape $s $msoShapeRoundedRectangle $x 2.05 2.27 3.62 $fill $(if($ch.Active){$C.Teal}else{$C.Line}) | Out-Null
        Add-Text $s $ch.No ($x + 0.22) 2.27 0.65 0.44 24 $fg $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $ch.Range ($x + 1.24) 2.37 0.77 0.22 9 $muted $true 3 'Aptos' 1 0 | Out-Null
        Add-Line $s ($x + 0.22) 2.94 ($x + 2.05) 2.94 $(if($ch.Active){$C.TealDark}else{$C.Line}) 1 | Out-Null
        Add-Text $s $ch.Name ($x + 0.22) 3.25 1.82 1.18 17 $fg $true 1 'Aptos Display' 1 0 | Out-Null
        $status = if ($ch.Active) { 'ĐANG TRÌNH BÀY' } else { 'TIẾP THEO' }
        Add-Text $s $status ($x + 0.22) 5.12 1.65 0.19 8 $muted $true 1 'Aptos' 1 0 | Out-Null
        $x += 2.45
    }
    Add-Text $s 'Thông điệp trung tâm' 0.68 6.19 1.60 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Tìm đúng sản phẩm — tư vấn có căn cứ — vận hành như một hệ thống hoàn chỉnh.' 2.23 6.11 9.95 0.38 15 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 2

    # 03 — Context
    $s = $deck.Slides.Add(3, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Bối cảnh' 'Tìm kiếm mua sắm đang chuyển từ từ khóa sang đa phương thức' 'Nhu cầu thực tế đồng thời chứa ngữ nghĩa, hình ảnh tham chiếu và ngữ cảnh hội thoại.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 2.02 3.26 3.72 $C.Card $C.Blue | Out-Null
    Add-Text $s 'QUY MÔ HÀNH VI' 0.98 2.30 1.82 0.22 10 $C.Blue $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s '≈ 20 tỷ' 0.98 2.79 2.42 0.54 28 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'lượt tìm kiếm trực quan bằng Google Lens mỗi tháng' 0.98 3.34 2.52 0.68 13 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 0.98 4.20 3.62 4.20 $C.Line 1 | Out-Null
    Add-Text $s '20%' 0.98 4.46 1.30 0.50 24 $C.Teal $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'liên quan đến mua sắm' 2.02 4.53 1.45 0.42 11 $C.White $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s '[1] Google, 2024' 0.98 5.28 2.30 0.20 8 $C.Gray $false 1 'Aptos' 1 0 | Out-Null

    $signals=@(
        @{Y=2.02;N='01';T='Văn bản';D='Mô tả phong cách, giá và mục đích bằng ngôn ngữ tự nhiên.';C=$C.Blue},
        @{Y=3.28;N='02';T='Hình ảnh';D='Ảnh tham chiếu mang tín hiệu khó diễn đạt thành từ khóa.';C=$C.Orange},
        @{Y=4.54;N='03';T='Hội thoại';D='Câu hỏi tiếp nối phụ thuộc kết quả và ràng buộc lượt trước.';C=$C.Teal}
    )
    foreach($item in $signals){
        Add-Shape $s $msoShapeRoundedRectangle 4.24 $item.Y 8.40 1.02 $C.Navy2 $C.Line | Out-Null
        Add-CircleLabel $s $item.N 4.52 ($item.Y+0.22) 0.48 $item.C $C.Navy 10
        Add-Text $s $item.T 5.24 ($item.Y+0.15) 1.35 0.28 15 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $item.D 6.62 ($item.Y+0.13) 5.55 0.48 11 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 6.02 11.96 0.72 $C.Teal $C.Teal | Out-Null
    Add-Text $s 'XU HƯỚNG CÔNG NGHỆ' 0.95 6.25 1.90 0.20 9 $C.TealDark $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'RAG gắn sinh ngôn ngữ với dữ liệu truy xuất [2] · CLIP học biểu diễn ảnh–văn bản từ 400 triệu cặp [3].' 2.80 6.16 9.35 0.36 11 $C.Navy $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 3

    # 04 — Real problem
    $s = $deck.Slides.Add(4, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Bài toán thực tế' 'Ba “điểm gãy” trong hành trình tìm sản phẩm' 'Khi từng tín hiệu bị xử lý rời rạc, kết quả khó phản ánh đầy đủ ý định mua sắm.'
    $problems = @(
        @{N='01'; Title='Khoảng cách ngữ nghĩa'; Desc='Từ khóa không biểu đạt hết nhu cầu, phong cách và mục đích sử dụng.'; Color=$C.Blue},
        @{N='02'; Title='Khoảng cách thị giác'; Desc='Ảnh tham chiếu khó chuyển thành thuộc tính để truy vấn danh mục sản phẩm.'; Color=$C.Orange},
        @{N='03'; Title='Mất ngữ cảnh hội thoại'; Desc='Câu hỏi tiếp nối phụ thuộc lựa chọn, bộ lọc và sản phẩm ở lượt trước.'; Color=$C.Teal}
    )
    $y = 2.02
    foreach ($p in $problems) {
        Add-Shape $s $msoShapeRoundedRectangle 0.68 $y 7.15 1.20 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $p.N 0.94 ($y + 0.29) 0.62 $p.Color $C.Navy 14
        Add-Text $s $p.Title 1.82 ($y + 0.20) 2.46 0.30 16 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $p.Desc 4.30 ($y + 0.18) 3.13 0.72 11 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
        $y += 1.39
    }
    Add-Shape $s $msoShapeRoundedRectangle 8.22 2.02 4.42 3.98 $C.White $C.White | Out-Null
    Add-Text $s 'HỆ QUẢ' 8.57 2.36 1.1 0.23 10 $C.Red $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Nhiều kết quả' 8.57 2.91 2.8 0.38 22 $C.Ink $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'nhưng ít lựa chọn phù hợp' 8.57 3.32 3.48 0.74 22 $C.Ink $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Line $s 8.57 4.30 12.21 4.30 (Rgb 213 224 231) 1 | Out-Null
    $effects = @('Tốn thời gian sàng lọc', 'Khó so sánh và ra quyết định', 'Trải nghiệm bị đứt đoạn')
    $ey = 4.55
    foreach ($e in $effects) {
        Add-Shape $s $msoShapeOval 8.60 ($ey + 0.04) 0.11 0.11 $C.Red | Out-Null
        Add-Text $s $e 8.86 $ey 3.05 0.25 11 $C.Gray $false 1 'Aptos' 1 0 | Out-Null
        $ey += 0.39
    }
    Add-Text $s 'Câu hỏi thiết kế' 0.68 6.37 1.55 0.21 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Làm thế nào hiểu đúng nhu cầu và nối nó với dữ liệu sản phẩm có thể kiểm chứng?' 2.20 6.27 10.15 0.40 16 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 4

    # 05 — Objectives
    $s = $deck.Slides.Add(5, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Mục tiêu đề tài' 'Xây dựng và đánh giá một trợ lý mua sắm đa phương thức' 'Không dừng ở mô hình AI: giải pháp phải tích hợp được vào toàn bộ hệ thống thương mại điện tử.'
    $objectives = @(
        @{N='01'; Title='Tìm kiếm đa phương thức'; Desc='Văn bản · hình ảnh · truy vấn kết hợp'; Color=$C.Blue},
        @{N='02'; Title='Tư vấn có căn cứ'; Desc='RAG trên dữ liệu sản phẩm và bộ nhớ hội thoại'; Color=$C.Teal},
        @{N='03'; Title='Tích hợp end-to-end'; Desc='Frontend · Backend · AI Service · MySQL · Qdrant'; Color=$C.Orange},
        @{N='04'; Title='Đánh giá có hệ thống'; Desc='Chất lượng truy hồi · độ trễ · chức năng · bảo mật'; Color=$C.Red}
    )
    $positions = @(@(0.68,2.05), @(6.78,2.05), @(0.68,4.08), @(6.78,4.08))
    for ($i=0; $i -lt 4; $i++) {
        $o = $objectives[$i]; $px=$positions[$i][0]; $py=$positions[$i][1]
        Add-Shape $s $msoShapeRoundedRectangle $px $py 5.87 1.67 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $o.N ($px + 0.27) ($py + 0.40) 0.70 $o.Color $C.Navy 14
        Add-Text $s $o.Title ($px + 1.20) ($py + 0.28) 4.25 0.35 18 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $o.Desc ($px + 1.20) ($py + 0.78) 4.25 0.54 12 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Text $s 'Tiêu chí xuyên suốt' 0.68 6.25 1.77 0.21 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Phù hợp · Có căn cứ · Nhất quán · Đo lường được' 2.47 6.15 9.50 0.39 16 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 5

    # 06 — Scope and users
    $s = $deck.Slides.Add(6, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Phạm vi & người dùng' 'Một nguyên mẫu thương mại điện tử thời trang hoàn chỉnh' 'Đánh giá trong môi trường cục bộ và Google Cloud, trên dữ liệu sản phẩm đã chuẩn hóa.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 2.00 3.23 4.28 $C.Card $C.Line | Out-Null
    Add-Text $s 'NGƯỜI DÙNG' 0.98 2.34 1.54 0.23 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-CircleLabel $s 'KH' 0.98 2.91 0.72 $C.Blue $C.White 13
    Add-Text $s 'Khách hàng' 1.93 2.91 1.55 0.29 17 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Khám phá · nhận tư vấn · mua và theo dõi đơn hàng' 1.93 3.27 1.61 0.70 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 0.98 4.20 3.60 4.20 $C.Line 1 | Out-Null
    Add-CircleLabel $s 'QT' 0.98 4.59 0.72 $C.Orange $C.Navy 13
    Add-Text $s 'Quản trị viên' 1.93 4.58 1.66 0.29 17 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Quản lý danh mục · đơn hàng · người dùng · khuyến mãi' 1.93 4.95 1.65 0.78 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null

    Add-Shape $s $msoShapeRoundedRectangle 4.19 2.00 4.18 4.28 $C.Teal $C.Teal | Out-Null
    Add-Text $s 'TRONG PHẠM VI' 4.53 2.34 2.1 0.23 10 $C.TealDark $true 1 'Aptos' 1 0 | Out-Null
    $inside = @('Tìm kiếm văn bản, hình ảnh và kết hợp', 'Tư vấn RAG nhiều lượt có bộ nhớ', 'Đồng bộ dữ liệu MySQL — Qdrant', 'Web thương mại điện tử và quản trị', 'Kiểm thử chức năng và phi chức năng')
    $iy = 2.89
    foreach ($item in $inside) {
        Add-CircleLabel $s '✓' 4.53 ($iy - 0.02) 0.29 $C.Navy $C.Teal 11
        Add-Text $s $item 5.00 $iy 2.92 0.47 11 $C.Navy $true 1 'Aptos' 1 0 | Out-Null
        $iy += 0.61
    }

    Add-Shape $s $msoShapeRoundedRectangle 8.65 2.00 3.99 4.28 $C.Card $C.Line | Out-Null
    Add-Text $s 'NGOÀI PHẠM VI' 8.99 2.34 2.1 0.23 10 $C.Red $true 1 'Aptos' 1 0 | Out-Null
    $outside = @('Thanh toán trực tuyến thực tế', 'Vận chuyển và chuỗi cung ứng', 'Quản lý kho quy mô lớn', 'Triển khai thương mại phân tán')
    $oy = 2.95
    foreach ($item in $outside) {
        Add-Text $s '—' 9.00 $oy 0.28 0.30 14 $C.Red $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $item 9.42 $oy 2.72 0.50 11 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
        $oy += 0.72
    }
    Add-Footer $s 6

    # 07 — Related approaches
    $s = $deck.Slides.Add(7, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Khảo sát giải pháp liên quan' 'Shopee, Tiki và Google Lens giải quyết từng phần của bài toán' 'So sánh theo chức năng được công bố trong các nguồn tham khảo của báo cáo.'
    $solutions=@(
        @{X=0.68;Y=1.94;T='Shopee';A='Từ khóa · bộ lọc · tìm bằng hình ảnh';P='+ Danh mục lớn; thao tác tìm kiếm quen thuộc';M='− Truy vấn ảnh riêng; nguồn khảo sát chưa mô tả hội thoại nhiều lượt';R='[4]';C=$C.Orange},
        @{X=6.78;Y=1.94;T='Tiki';A='Từ khóa · lọc nhanh · sản phẩm tương tự';P='+ Gắn tìm kiếm với hệ sinh thái mua sắm';M='− Nguồn công khai chưa đặc tả duy trì ràng buộc qua nhiều lượt';R='[5]';C=$C.Blue},
        @{X=0.68;Y=4.08;T='Google Lens';A='Hình ảnh + văn bản → tinh chỉnh thuộc tính';P='+ Đầu vào đa phương thức tự nhiên';M='− Không phải quy trình tư vấn và giao dịch của một sàn cụ thể';R='[6]';C=$C.Teal},
        @{X=6.78;Y=4.08;T='Giải pháp đề xuất';A='Text · Image · Hybrid + RAG + memory';P='+ Hội thoại nhiều lượt; Backend xác nhận dữ liệu hiện hành';M='− Nguyên mẫu thời trang ở quy mô 1.000 sản phẩm';R='Nội bộ';C=$C.Red;H=$true}
    )
    foreach($sol in $solutions){
        $fill=if($sol.ContainsKey('H')){$C.Card}else{$C.Navy2}
        Add-Shape $s $msoShapeRoundedRectangle $sol.X $sol.Y 5.86 1.82 $fill $sol.C | Out-Null
        Add-Shape $s $msoShapeRectangle $sol.X $sol.Y 0.09 1.82 $sol.C | Out-Null
        Add-Text $s $sol.T ($sol.X+0.30) ($sol.Y+0.18) 3.78 0.30 16 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $sol.R ($sol.X+4.72) ($sol.Y+0.20) 0.70 0.22 9 $sol.C $true 3 'Aptos' 1 0 | Out-Null
        Add-Text $s $sol.A ($sol.X+0.30) ($sol.Y+0.60) 5.12 0.32 11 $sol.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $sol.P ($sol.X+0.30) ($sol.Y+1.02) 5.10 0.25 10 $C.White $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $sol.M ($sol.X+0.30) ($sol.Y+1.35) 5.10 0.34 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Text $s 'Nguồn: [4] Shopee Việt Nam · [5] Tiki · [6] Google Multisearch. Chi tiết tại Chương 2 và slide 32.' 0.70 6.36 11.64 0.24 8 $C.Gray $false 1 'Aptos' 1 0 | Out-Null
    Add-Footer $s 7

    # 08 — Differentiation
    $s = $deck.Slides.Add(8, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Vòng lặp mua sắm' 'Từ nhu cầu đến hành động — rồi tiếp tục hiểu người dùng' 'Mỗi lựa chọn và phản hồi trở thành ngữ cảnh cho lượt tìm kiếm tiếp theo.'
    $steps = @(
        @{N='01'; A='HIỂU'; B='Văn bản + hình ảnh'; C=$C.Blue},
        @{N='02'; A='TRUY HỒI'; B='Vector + ràng buộc'; C=$C.Orange},
        @{N='03'; A='TƯ VẤN'; B='RAG + bộ nhớ'; C=$C.Teal},
        @{N='04'; A='HÀNH ĐỘNG'; B='Mua hàng + phản hồi'; C=$C.Red}
    )
    $sx = 0.68
    for ($i=0; $i -lt 4; $i++) {
        $st=$steps[$i]
        Add-Shape $s $msoShapeRoundedRectangle $sx 2.20 2.63 2.30 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $st.N ($sx+0.28) 2.51 0.68 $st.C $C.Navy 13
        Add-Text $s $st.A ($sx+0.28) 3.35 2.05 0.30 13 $st.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $st.B ($sx+0.28) 3.78 2.05 0.42 16 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        if ($i -lt 3) {
            Add-CircleLabel $s '→' ($sx+2.69) 3.04 0.48 $C.Navy2 $C.Muted 14
        }
        $sx += 3.03
    }
    Add-Shape $s $msoShapeRoundedRectangle 1.88 5.10 9.58 1.05 $C.Navy2 $C.Teal | Out-Null
    Add-Text $s '↺' 2.22 5.28 0.62 0.48 26 $C.Teal $true 2 'Aptos Display' 3 0 | Out-Null
    Add-Text $s 'Phản hồi · lựa chọn · ràng buộc mới' 3.00 5.30 3.62 0.30 16 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'được lưu vào bộ nhớ và quay lại bước HIỂU' 6.62 5.31 4.30 0.28 12 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Footer $s 8

    # 09 — Functional requirements
    $s = $deck.Slides.Add(9, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Yêu cầu chức năng' '17 yêu cầu tạo thành một hành trình mua sắm liền mạch' '12 yêu cầu AI mở rộng trên 5 năng lực thương mại điện tử cốt lõi.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 2.02 8.85 1.52 $C.Card $C.Line | Out-Null
    Add-Text $s 'HÀNH TRÌNH THƯƠNG MẠI ĐIỆN TỬ' 0.98 2.27 3.15 0.22 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    $commerce = @('Tài khoản','Khám phá sản phẩm','Giỏ hàng','Đặt hàng COD','Theo dõi & đánh giá')
    $cx = 0.98
    for ($i=0; $i -lt $commerce.Count; $i++) {
        Add-CircleLabel $s ('{0:D2}' -f ($i+1)) $cx 2.72 0.43 $(if($i -eq 3){$C.Orange}else{$C.Blue}) $C.White 9
        Add-Text $s $commerce[$i] ($cx + 0.52) 2.69 1.05 0.48 10 $C.White $true 1 'Aptos' 1 0 | Out-Null
        if ($i -lt 4) { Add-Text $s '›' ($cx + 1.45) 2.74 0.23 0.24 14 $C.Line $true 2 'Aptos' 1 0 | Out-Null }
        $cx += 1.66
    }
    Add-Shape $s $msoShapeRoundedRectangle 9.80 2.02 2.84 1.52 $C.Teal $C.Teal | Out-Null
    Add-Text $s '17' 10.08 2.23 0.92 0.64 31 $C.Navy $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'YÊU CẦU' 10.95 2.34 1.23 0.22 10 $C.TealDark $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s '12 AI  +  5 E-commerce' 10.08 2.95 2.10 0.26 11 $C.Navy $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'TRỢ LÝ MUA SẮM ĐA PHƯƠNG THỨC' 0.68 3.94 3.42 0.22 10 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    $aiCaps = @(
        @{N='01–03';T='Tìm kiếm';D='Text · Image · Hybrid';C=$C.Blue},
        @{N='04–05';T='Hiểu & lọc';D='Thuộc tính · metadata';C=$C.Orange},
        @{N='06–07';T='Hội thoại';D='Bộ nhớ · có căn cứ';C=$C.Teal},
        @{N='08–09';T='Xếp hạng';D='Fusion · rerank · tương tự';C=$C.Red},
        @{N='10–11';T='Vận hành';D='Đồng bộ · log · latency';C=$C.Blue},
        @{N='12';T='Dự phòng';D='Nghiệp vụ lõi vẫn hoạt động';C=$C.Orange}
    )
    $ax = 0.68
    foreach ($cap in $aiCaps) {
        Add-Shape $s $msoShapeRoundedRectangle $ax 4.34 1.88 1.62 $C.Navy2 $C.Line | Out-Null
        Add-Text $s $cap.N ($ax + 0.19) 4.57 0.64 0.20 9 $cap.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $cap.T ($ax + 0.19) 4.91 1.48 0.28 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $cap.D ($ax + 0.19) 5.33 1.48 0.38 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
        $ax += 2.02
    }
    Add-Text $s 'Nguyên tắc ưu tiên' 0.68 6.42 1.60 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Tìm đúng trước — giải thích có căn cứ — không làm gián đoạn nghiệp vụ.' 2.25 6.33 9.86 0.38 15 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 9 'PHÂN TÍCH & THIẾT KẾ'

    # 10 — Non-functional requirements
    $s = $deck.Slides.Add(10, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Yêu cầu phi chức năng' '9 yêu cầu biến nguyên mẫu AI thành một hệ thống có thể vận hành' 'Các mục tiêu được đặt theo quy mô thử nghiệm và có bằng chứng kiểm tra ở phần đánh giá.'
    $metrics = @(
        @{V='1–3s';L='Nghiệp vụ lõi';C=$C.Blue},
        @{V='2–5s';L='Tác vụ AI';C=$C.Teal},
        @{V='500–2.000';L='Sản phẩm';C=$C.Orange},
        @{V='< 50';L='Người dùng đồng thời';C=$C.Red}
    )
    $mx=0.68
    foreach($m in $metrics){
        Add-Shape $s $msoShapeRoundedRectangle $mx 2.00 2.88 1.03 $C.Card $C.Line | Out-Null
        Add-Text $s $m.V ($mx+0.22) 2.20 1.20 0.38 22 $m.C $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $m.L ($mx+1.38) 2.25 1.25 0.34 10 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
        $mx += 3.08
    }
    $pillars = @(
        @{T='An toàn & đúng đắn';N='NFR-02 · 04 · 08';D='RBAC, BCrypt; MySQL là nguồn chuẩn; lỗi vector không làm sai giao dịch.';C=$C.Red},
        @{T='Khả dụng & tương thích';N='NFR-03 · 06';D='AI suy giảm độc lập; Chrome, Edge, Firefox; laptop và điện thoại.';C=$C.Blue},
        @{T='Bảo trì & mở rộng';N='NFR-05 · 09';D='Mô-đun hóa; provider và mô hình được thay bằng cấu hình/adapter.';C=$C.Orange},
        @{T='Quan sát & đo lường';N='NFR-01 · 07';D='Health check, correlation ID, log latency, retrieval, rerank và checkpoint.';C=$C.Teal}
    )
    $ppos=@(@(0.68,3.42),@(6.78,3.42),@(0.68,5.02),@(6.78,5.02))
    for($i=0;$i -lt 4;$i++){
        $p=$pillars[$i];$px=$ppos[$i][0];$py=$ppos[$i][1]
        Add-Shape $s $msoShapeRoundedRectangle $px $py 5.86 1.31 $C.Navy2 $C.Line | Out-Null
        Add-Shape $s $msoShapeRectangle $px $py 0.08 1.31 $p.C | Out-Null
        Add-Text $s $p.T ($px+0.29) ($py+0.18) 2.28 0.29 15 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $p.N ($px+3.90) ($py+0.20) 1.55 0.20 9 $p.C $true 3 'Aptos' 1 0 | Out-Null
        Add-Text $s $p.D ($px+0.29) ($py+0.65) 5.20 0.48 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Footer $s 10 'PHÂN TÍCH & THIẾT KẾ'

    # 11 — Use case overview
    $s = $deck.Slides.Add(11, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Use case tổng quan' 'Ba tác nhân — ba vùng trách nhiệm — một hành trình thống nhất' 'Spring Boot kiểm soát nghiệp vụ; AI Service cung cấp tìm kiếm, tư vấn và đồng bộ chỉ mục.'
    $actors = @(
        @{X=0.68;Code='KH';Title='Khách hàng';Color=$C.Blue;Items=@('Tài khoản & hồ sơ','Khám phá & so sánh','Giỏ hàng & COD','Theo dõi & đánh giá','Sử dụng trợ lý AI')},
        @{X=4.74;Code='QT';Title='Quản trị viên';Color=$C.Orange;Items=@('Quản lý danh mục','Sản phẩm & tồn kho','Đơn hàng & người dùng','Khuyến mãi & nội dung','Kích hoạt đồng bộ AI')},
        @{X=8.80;Code='AI';Title='AI Service';Color=$C.Teal;Items=@('Text / Image / Hybrid','Chat nhiều lượt','Fusion & rerank','Phản hồi an toàn','Index / delete / health')}
    )
    foreach($a in $actors){
        Add-Shape $s $msoShapeRoundedRectangle $a.X 2.04 3.56 4.34 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $a.Code ($a.X+0.28) 2.32 0.66 $a.Color $(if($a.Code -eq 'QT'){$C.Navy}else{$C.White}) 13
        Add-Text $s $a.Title ($a.X+1.15) 2.37 2.00 0.32 18 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Line $s ($a.X+0.28) 3.18 ($a.X+3.28) 3.18 $C.Line 1 | Out-Null
        $uy=3.45
        foreach($item in $a.Items){
            Add-Shape $s $msoShapeOval ($a.X+0.32) ($uy+0.08) 0.10 0.10 $a.Color | Out-Null
            Add-Text $s $item ($a.X+0.58) $uy 2.54 0.34 11 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
            $uy += 0.49
        }
        Add-Text $s $(if($a.Code -eq 'KH'){'Mọi khách hàng'}elseif($a.Code -eq 'QT'){'Vai trò ADMIN'}else{'Tác nhân hệ thống'}) ($a.X+0.30) 6.00 2.90 0.20 8 $a.Color $true 1 'Aptos' 1 0 | Out-Null
    }
    Add-Text $s 'Quan hệ chính' 0.68 6.65 1.28 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Khách hàng yêu cầu → Backend xác nhận → AI hỗ trợ → Backend trả dữ liệu hiện hành.' 1.95 6.56 10.45 0.37 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 11 'PHÂN TÍCH & THIẾT KẾ'

    # 12 — System architecture
    $s = $deck.Slides.Add(12, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Kiến trúc tổng thể hệ thống' 'Một cổng công khai, hai miền xử lý, ba lớp lưu trữ' 'Frontend chỉ giao tiếp với Spring Boot; AI Service và các kho dữ liệu nằm sau ranh giới dịch vụ.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 1.92 12.00 4.52 $C.White $C.Line | Out-Null
    Add-PictureContain $s $architecturePath 0.94 2.15 11.48 3.56 | Out-Null
    $principles=@(
        @{X=0.95;T='Spring Boot';D='Cổng API & quyết định nghiệp vụ';C=$C.Blue},
        @{X=4.78;T='AI Service';D='Truy hồi & tư vấn, có thể suy giảm';C=$C.Teal},
        @{X=8.61;T='MySQL → Qdrant';D='Nguồn chuẩn → chỉ mục dẫn xuất';C=$C.Orange}
    )
    foreach($p in $principles){
        Add-Shape $s $msoShapeRoundedRectangle $p.X 5.71 3.54 0.48 $C.Navy2 $p.C | Out-Null
        Add-Text $s $p.T ($p.X+0.16) 5.80 1.02 0.18 9 $p.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $p.D ($p.X+1.14) 5.78 2.17 0.24 9 $C.White $true 1 'Aptos' 1 0 | Out-Null
    }
    Add-Text $s 'Ranh giới tin cậy' 0.68 6.69 1.53 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'AI đề xuất định danh; Backend xác nhận giá, tồn kho và dữ liệu trả về.' 2.18 6.59 9.80 0.38 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 12 'PHÂN TÍCH & THIẾT KẾ'

    # 13 — Main flow
    $s = $deck.Slides.Add(13, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Luồng hoạt động chính' 'Từ yêu cầu đa phương thức đến sản phẩm có thể mua' 'Pipeline tách rõ bước hiểu truy vấn, truy hồi vector và xác nhận nghiệp vụ.'
    $flow=@(
        @{N='01';T='Đầu vào';D='Text · ảnh · ngữ cảnh';C=$C.Blue},
        @{N='02';T='Hiểu truy vấn';D='Ý định · thuộc tính · ràng buộc';C=$C.Orange},
        @{N='03';T='Biểu diễn';D='Text / image embedding';C=$C.Teal},
        @{N='04';T='Truy hồi';D='Qdrant + metadata filter';C=$C.Blue},
        @{N='05';T='Xếp hạng';D='Fusion · rerank · top-k';C=$C.Red},
        @{N='06';T='Xác nhận';D='Giá · tồn kho từ MySQL';C=$C.Orange},
        @{N='07';T='Phản hồi';D='Kết quả + câu trả lời RAG';C=$C.Teal}
    )
    $fx=0.68
    foreach($f in $flow){
        Add-Shape $s $msoShapeRoundedRectangle $fx 2.35 1.55 2.52 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $f.N ($fx+0.18) 2.59 0.48 $f.C $C.Navy 10
        Add-Text $s $f.T ($fx+0.18) 3.31 1.18 0.54 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $f.D ($fx+0.18) 4.01 1.18 0.54 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
        if($f.N -ne '07'){ Add-Text $s '→' ($fx+1.55) 3.33 0.30 0.40 16 $C.Line $true 2 'Aptos' 3 0 | Out-Null }
        $fx += 1.72
    }
    Add-Shape $s $msoShapeRoundedRectangle 1.43 5.33 10.47 0.83 $C.Navy2 $C.Line | Out-Null
    Add-Text $s 'Bộ nhớ hội thoại' 1.72 5.56 1.74 0.24 11 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 3.46 5.72 9.52 5.72 $C.Teal 1.5 | Out-Null
    Add-Text $s 'Khôi phục ràng buộc trước đó' 3.72 5.50 2.35 0.28 10 $C.White $false 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Lưu lựa chọn mới cho lượt tiếp theo' 8.37 5.50 2.98 0.28 10 $C.White $false 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Nhánh suy giảm' 0.68 6.55 1.35 0.20 9 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Một tín hiệu lỗi → dùng nhánh còn lại · AI lỗi → website và nghiệp vụ lõi vẫn hoạt động.' 2.02 6.46 10.38 0.38 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 13 'PHÂN TÍCH & THIẾT KẾ'

    # 14 — Data design
    $s = $deck.Slides.Add(14, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Thiết kế cơ sở dữ liệu' 'Dữ liệu được chia theo miền, nhưng quyền sở hữu phải rõ ràng' 'MySQL giữ giao dịch; Qdrant và Redis phục vụ AI, có thể tái tạo hoặc thay thế.'
    Add-Text $s '7 MIỀN DỮ LIỆU NGHIỆP VỤ' 0.68 2.00 2.72 0.22 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    $domains=@(
        @{T='Người dùng & phân quyền';C=$C.Blue},@{T='Danh mục & sản phẩm';C=$C.Teal},
        @{T='Kho & giữ hàng';C=$C.Orange},@{T='Giỏ hàng & tương tác';C=$C.Red},
        @{T='Đơn hàng & vận chuyển';C=$C.Blue},@{T='Thanh toán & khuyến mãi';C=$C.Orange},
        @{T='Chat & đồng bộ AI';C=$C.Teal}
    )
    $dpos=@(@(0.68,2.39),@(3.49,2.39),@(0.68,3.45),@(3.49,3.45),@(0.68,4.51),@(3.49,4.51),@(0.68,5.57))
    for($i=0;$i -lt $domains.Count;$i++){
        $d=$domains[$i];$dx=$dpos[$i][0];$dy=$dpos[$i][1]
        $dw=if($i -eq 6){5.56}else{2.66}
        Add-Shape $s $msoShapeRoundedRectangle $dx $dy $dw 0.78 $C.Card $C.Line | Out-Null
        Add-Shape $s $msoShapeRectangle $dx $dy 0.08 0.78 $d.C | Out-Null
        Add-Text $s $d.T ($dx+0.25) ($dy+0.19) ($dw-0.46) 0.34 11 $C.White $true 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 6.62 2.00 6.02 4.35 $C.Card $C.Line | Out-Null
    Add-Text $s 'QUYỀN SỞ HỮU DỮ LIỆU' 6.95 2.31 2.40 0.22 10 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 7.00 2.83 2.24 2.18 $C.Teal $C.Teal | Out-Null
    Add-Text $s 'MySQL' 7.34 3.20 1.55 0.39 22 $C.Navy $true 2 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Nguồn dữ liệu chuẩn' 7.25 3.78 1.72 0.28 11 $C.TealDark $true 2 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Giao dịch · giá · tồn kho' 7.20 4.25 1.82 0.28 9 $C.Navy $false 2 'Aptos' 1 0 | Out-Null
    Add-Text $s '→' 9.38 3.62 0.50 0.48 22 $C.Line $true 2 'Aptos' 3 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 9.99 2.74 2.17 1.02 $C.Navy2 $C.Blue | Out-Null
    Add-Text $s 'Qdrant' 10.26 2.95 1.64 0.26 15 $C.Blue $true 2 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Chỉ mục vector dẫn xuất' 10.19 3.34 1.76 0.19 8 $C.Muted $false 2 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 9.99 4.12 2.17 1.02 $C.Navy2 $C.Orange | Out-Null
    Add-Text $s 'Redis' 10.26 4.33 1.64 0.26 15 $C.Orange $true 2 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Cache & checkpoint' 10.19 4.72 1.76 0.19 8 $C.Muted $false 2 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Có thể tái tạo' 9.98 5.57 2.20 0.22 10 $C.Teal $true 2 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Không quyết định giao dịch' 9.70 5.91 2.76 0.24 10 $C.White $false 2 'Aptos' 1 0 | Out-Null
    Add-Footer $s 14 'PHÂN TÍCH & THIẾT KẾ'

    # 15 — Technology choices
    $s = $deck.Slides.Add(15, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Công nghệ sử dụng & lý do lựa chọn' 'Mỗi công nghệ được chọn theo vai trò, không theo xu hướng' 'Tiêu chí: phù hợp kiến trúc, khả năng thay thế, hiệu năng, chi phí và khả năng tái lập.'
    $tech=@(
        @{Y=2.02;Layer='GIAO DIỆN';Stack='React · Redux Toolkit · Axios';Why='SPA theo component; quản lý trạng thái và giao tiếp API nhất quán.';C=$C.Blue},
        @{Y=2.93;Layer='NGHIỆP VỤ';Stack='Java · Spring Boot · Security · JPA';Why='Transaction, phân quyền và hệ sinh thái backend trưởng thành.';C=$C.Orange},
        @{Y=3.84;Layer='AI SERVICE';Stack='Python · FastAPI · Pydantic · LangGraph';Why='Tích hợp thư viện ML; workflow hội thoại có trạng thái và nhiều nhánh.';C=$C.Teal},
        @{Y=4.75;Layer='DỮ LIỆU';Stack='MySQL · Qdrant · Redis';Why='Tách giao dịch, truy hồi vector và cache/checkpoint đúng trách nhiệm.';C=$C.Red},
        @{Y=5.66;Layer='MÔ HÌNH & HẠ TẦNG';Stack='Bedrock · Cohere Embed v4 · YOLO · Docker · GCP';Why='Managed-first; crop ảnh tùy chọn; triển khai và tái lập bằng container.';C=$C.Blue}
    )
    foreach($t in $tech){
        Add-Shape $s $msoShapeRoundedRectangle 0.68 $t.Y 12.00 0.72 $C.Card $C.Line | Out-Null
        Add-Shape $s $msoShapeRoundedRectangle 0.68 $t.Y 1.82 0.72 $t.C $t.C | Out-Null
        Add-Text $s $t.Layer 0.86 ($t.Y+0.18) 1.45 0.24 9 $C.Navy $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $t.Stack 2.78 ($t.Y+0.16) 3.82 0.30 13 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Line $s 6.76 ($t.Y+0.14) 6.76 ($t.Y+0.58) $C.Line 1 | Out-Null
        Add-Text $s $t.Why 7.02 ($t.Y+0.14) 5.20 0.42 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Footer $s 15 'PHÂN TÍCH & THIẾT KẾ'

    # 16 — Key technical decisions
    $s = $deck.Slides.Add(16, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Các quyết định kỹ thuật quan trọng' 'Bốn “đường biên” giữ hệ thống đúng, bền và có thể thay đổi' 'Mỗi quyết định trực tiếp trả lời một rủi ro kiến trúc hoặc yêu cầu phi chức năng.'
    $decisions=@(
        @{N='01';Risk='Bề mặt tấn công & logic phân tán';Decision='Spring Boot là cổng công khai duy nhất';Effect='JWT, phân quyền và nghiệp vụ được kiểm soát tại một nơi.';C=$C.Blue},
        @{N='02';Risk='Vector lệch dữ liệu giao dịch';Decision='MySQL là source of truth';Effect='Qdrant chỉ là chỉ mục dẫn xuất, có thể đồng bộ hoặc tái tạo.';C=$C.Teal},
        @{N='03';Risk='AI lỗi làm dừng website';Decision='Tách AI Service và có fallback';Effect='Danh mục, giỏ hàng và đơn hàng tiếp tục hoạt động độc lập.';C=$C.Orange},
        @{N='04';Risk='Khóa chặt vào provider/mô hình';Decision='Adapter + cấu hình + quan sát';Effect='Thay embedding, LLM, reranker; đo từng bước bằng correlation ID.';C=$C.Red}
    )
    $dy=2.02
    foreach($d in $decisions){
        Add-Shape $s $msoShapeRoundedRectangle 0.68 $dy 12.00 1.05 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $d.N 0.94 ($dy+0.23) 0.58 $d.C $C.Navy 12
        Add-Text $s 'RỦI RO' 1.74 ($dy+0.17) 0.70 0.18 8 $C.Gray $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $d.Risk 1.74 ($dy+0.46) 2.46 0.36 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
        Add-Line $s 4.37 ($dy+0.16) 4.37 ($dy+0.88) $C.Line 1 | Out-Null
        Add-Text $s 'QUYẾT ĐỊNH' 4.66 ($dy+0.17) 1.03 0.18 8 $d.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $d.Decision 4.66 ($dy+0.45) 2.86 0.36 13 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Line $s 7.72 ($dy+0.16) 7.72 ($dy+0.88) $C.Line 1 | Out-Null
        Add-Text $s 'TÁC ĐỘNG' 8.01 ($dy+0.17) 0.85 0.18 8 $C.Gray $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $d.Effect 8.01 ($dy+0.43) 4.20 0.42 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
        $dy += 1.19
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 6.92 12.00 0.01 $C.Teal | Out-Null
    Add-Text $s 'Kết quả: AI hỗ trợ quyết định — Backend bảo toàn nghiệp vụ — dữ liệu luôn có nguồn chuẩn.' 0.92 6.54 11.48 0.30 14 $C.White $true 2 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 16 'PHÂN TÍCH & THIẾT KẾ'

    # 17 — Completed product overview
    $s = $deck.Slides.Add(17, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Tổng quan sản phẩm hoàn thiện' 'Một sản phẩm hoàn chỉnh, không chỉ một mô hình AI' 'Ba không gian trải nghiệm dùng chung dữ liệu, nghiệp vụ và cơ chế xác thực.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 1.96 7.48 3.72 $C.White $C.Line | Out-Null
    Add-PictureContain $s $homePath 0.84 2.12 7.16 3.40 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 8.44 1.96 4.20 1.78 $C.White $C.Line | Out-Null
    Add-PictureContain $s $assistantPath 8.57 2.09 3.94 1.52 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 8.44 3.90 4.20 1.78 $C.Navy2 $C.Line | Out-Null
    Add-PictureContain $s $adminPath 8.57 4.03 3.94 1.52 | Out-Null
    $areas=@(
        @{X=0.68;N='01';T='Cửa hàng trực tuyến';D='Khám phá · mua hàng · theo dõi';C=$C.Blue},
        @{X=4.76;N='02';T='Trợ lý AI';D='Text · Image · Hybrid · Chat';C=$C.Teal},
        @{X=8.84;N='03';T='Backoffice';D='Dữ liệu · đơn hàng · đồng bộ';C=$C.Orange}
    )
    foreach($a in $areas){
        Add-CircleLabel $s $a.N $a.X 6.03 0.47 $a.C $C.Navy 10
        Add-Text $s $a.T ($a.X+0.62) 5.97 2.22 0.28 13 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $a.D ($a.X+0.62) 6.34 2.92 0.25 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Footer $s 17 'SẢN PHẨM & DEMO'

    # 18 — Featured function 1: multimodal search
    $s = $deck.Slides.Add(18, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Chức năng nổi bật 01' 'Một giao diện — ba cách diễn đạt nhu cầu' 'Người dùng có thể bắt đầu bằng mô tả, ảnh tham chiếu hoặc kết hợp cả hai.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 1.96 7.56 3.94 $C.White $C.Line | Out-Null
    Add-PictureContain $s $assistantPath 0.85 2.13 7.22 3.60 | Out-Null
    $modes=@(
        @{Y=2.02;N='01';T='Text Search';D='Hiểu ý định và các ràng buộc bằng ngôn ngữ tự nhiên.';C=$C.Blue},
        @{Y=3.29;N='02';T='Image Search';D='Tìm sản phẩm tương đồng từ đặc trưng thị giác.';C=$C.Orange},
        @{Y=4.56;N='03';T='Hybrid Search';D='Ảnh xác định kiểu dáng; văn bản bổ sung màu, giá, danh mục.';C=$C.Teal}
    )
    foreach($m in $modes){
        Add-Shape $s $msoShapeRoundedRectangle 8.52 $m.Y 4.12 1.08 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $m.N 8.77 ($m.Y+0.24) 0.52 $m.C $C.Navy 11
        Add-Text $s $m.T 9.50 ($m.Y+0.17) 2.55 0.29 15 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $m.D 9.50 ($m.Y+0.55) 2.72 0.35 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Text $s 'Pipeline' 0.68 6.37 0.82 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'YOLO crop (tùy chọn)  →  Embed v4  →  Qdrant  →  metadata filter  →  fusion / rerank' 1.53 6.28 10.90 0.38 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 18 'SẢN PHẨM & DEMO'

    # 19 — Featured function 2: grounded multi-turn assistant
    $s = $deck.Slides.Add(19, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Chức năng nổi bật 02' 'Trợ lý nhớ điều đã nói và trả lời từ dữ liệu sản phẩm' 'Hội thoại nhiều lượt được nối với retrieval, dữ liệu hiện hành và phản hồi an toàn.'
    $rag=@(
        @{Y=2.04;N='01';T='Memory';D='Khôi phục màu, giá, danh mục và lựa chọn ở lượt trước.';C=$C.Blue},
        @{Y=3.35;N='02';T='Retrieval';D='Tìm ứng viên liên quan thay vì trả lời từ trí nhớ mô hình.';C=$C.Teal},
        @{Y=4.66;N='03';T='Grounded response';D='Phản hồi gắn với sản phẩm, giá và tồn kho đã xác nhận.';C=$C.Orange}
    )
    foreach($r in $rag){
        Add-Shape $s $msoShapeRoundedRectangle 0.68 $r.Y 4.26 1.10 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $r.N 0.94 ($r.Y+0.25) 0.52 $r.C $C.Navy 11
        Add-Text $s $r.T 1.69 ($r.Y+0.17) 2.60 0.29 15 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $r.D 1.69 ($r.Y+0.55) 2.80 0.38 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 5.23 1.96 7.41 3.98 $C.White $C.Line | Out-Null
    Add-PictureContain $s $chatbotPath 5.40 2.13 7.07 3.64 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 0.68 6.16 11.96 0.62 $C.Navy2 $C.Line | Out-Null
    Add-Text $s 'Câu hỏi tiếp nối' 0.94 6.34 1.48 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s '“Mẫu thứ hai còn màu đen không?”  →  hệ thống hiểu “mẫu thứ hai” từ lượt trước.' 2.43 6.26 9.78 0.34 13 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 19 'SẢN PHẨM & DEMO'

    # 20 — Featured function 3: end-to-end commerce
    $s = $deck.Slides.Add(20, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Chức năng nổi bật 03' 'Từ tìm thấy đến đặt hàng trong cùng một hệ thống' 'Kết quả AI không dừng ở gợi ý; người dùng tiếp tục hành trình mua sắm với dữ liệu nhất quán.'
    $journey=@(
        @{X=0.68;Img=$catalogPath;N='01';T='Khám phá';C=$C.Blue},
        @{X=3.73;Img=$detailPath;N='02';T='Chọn sản phẩm';C=$C.Teal},
        @{X=6.78;Img=$cartPath;N='03';T='Kiểm tra giỏ';C=$C.Orange},
        @{X=9.83;Img=$checkoutPath;N='04';T='Đặt hàng COD';C=$C.Red}
    )
    foreach($j in $journey){
        Add-Shape $s $msoShapeRoundedRectangle $j.X 2.02 2.80 1.77 $C.White $C.Line | Out-Null
        Add-PictureContain $s $j.Img ($j.X+0.10) 2.12 2.60 1.48 | Out-Null
        Add-CircleLabel $s $j.N ($j.X+0.12) 3.98 0.42 $j.C $C.Navy 9
        Add-Text $s $j.T ($j.X+0.66) 3.95 1.90 0.28 12 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        if($j.N -ne '04'){ Add-Text $s '→' ($j.X+2.78) 2.71 0.27 0.34 15 $C.Line $true 2 'Aptos' 3 0 | Out-Null }
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 4.62 5.83 1.62 $C.Card $C.Line | Out-Null
    Add-Text $s 'GIAO DỊCH AN TOÀN' 0.97 4.88 1.95 0.20 9 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Kiểm tra tồn kho · coupon · địa chỉ' 0.97 5.28 3.72 0.28 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Tạo đơn trong transaction; rollback nếu bất kỳ bước nào thất bại.' 0.97 5.69 4.98 0.29 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 6.80 4.62 5.84 1.62 $C.Card $C.Line | Out-Null
    Add-PictureContain $s $adminPath 7.02 4.82 2.62 1.22 | Out-Null
    Add-Text $s 'BACKOFFICE' 9.92 4.87 1.36 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Vận hành sau mua' 9.92 5.23 2.12 0.28 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Đơn hàng · tồn kho · người dùng · đồng bộ AI' 9.92 5.63 2.30 0.40 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Footer $s 20 'SẢN PHẨM & DEMO'

    # 21 — Video demo
    $s = $deck.Slides.Add(21, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Video demo sản phẩm' 'Một luồng xuyên suốt trong 3–4 phút' 'Tập trung vào ba năng lực AI và cách chúng nối với hành trình mua hàng.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 1.96 3.30 4.63 $C.Card $C.Line | Out-Null
    Add-Text $s 'KỊCH BẢN DEMO' 0.98 2.28 1.78 0.22 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    $demoSteps=@(
        @{N='01';T='Text Search';C=$C.Blue},
        @{N='02';T='Image Search';C=$C.Orange},
        @{N='03';T='Hybrid Search';C=$C.Teal},
        @{N='04';T='Chat nhiều lượt';C=$C.Red},
        @{N='05';T='Giỏ hàng → COD';C=$C.Blue}
    )
    $vy=2.78
    foreach($d in $demoSteps){
        Add-CircleLabel $s $d.N 0.99 $vy 0.42 $d.C $C.Navy 9
        Add-Text $s $d.T 1.59 ($vy+0.04) 1.84 0.25 12 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        if($d.N -ne '05'){ Add-Line $s 1.20 ($vy+0.43) 1.20 ($vy+0.68) $C.Line 1 | Out-Null }
        $vy += 0.68
    }
    Add-Text $s 'Dự phòng' 0.99 6.25 0.78 0.18 8 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Demo trực tiếp + ảnh chụp luồng' 1.78 6.20 1.84 0.28 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 4.27 1.96 8.37 4.63 $C.Card $C.Line | Out-Null
    if (Test-Path $videoPath) {
        $media = $s.Shapes.AddMediaObject2($videoPath, $msoFalse, $msoTrue, (Pt 4.43), (Pt 2.12), (Pt 8.05), (Pt 3.82))
        $media.AnimationSettings.PlaySettings.PlayOnEntry = $msoFalse
    } else {
        Add-PictureFit $s $assistantPath 4.43 2.12 8.05 3.82 | Out-Null
        Add-Shape $s $msoShapeRectangle 4.43 2.12 8.05 3.82 $C.Navy -1 0 48 | Out-Null
        Add-CircleLabel $s '▶' 7.76 3.19 1.38 $C.Teal $C.Navy 27
        Add-Text $s 'DEMO SẢN PHẨM' 6.38 4.86 4.12 0.34 18 $C.White $true 2 'Aptos Display' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 4.72 6.14 7.72 0.45 $C.Navy2 $C.Line | Out-Null
    Add-Text $s 'TEXT  →  IMAGE  →  HYBRID  →  CHAT  →  CHECKOUT' 4.92 6.26 5.65 0.19 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    if (Test-Path $videoPath) {
        $backupLink = Add-Text $s 'MỞ FILE DỰ PHÒNG ↗' 10.48 6.24 1.72 0.22 8 $C.Orange $true 3 'Aptos' 1 0
        $backupLink.ActionSettings(1).Hyperlink.Address = 'assets/video/demo-san-pham.mp4'
    } else {
        Add-Text $s 'DEMO TRỰC TIẾP' 10.48 6.24 1.72 0.22 8 $C.Orange $true 3 'Aptos' 1 0 | Out-Null
    }
    Add-Footer $s 21 'SẢN PHẨM & DEMO'

    # 22 — Three-layer testing strategy and reproducible environment
    $s = $deck.Slides.Add(22, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Chiến lược & môi trường kiểm thử' 'Ba lớp kiểm chứng — từ mô hình đến khả năng vận hành' 'Mỗi lớp trả lời một nhóm câu hỏi nghiên cứu và lưu artifact để có thể tái lập.'
    $testLayers=@(
        @{X=0.68;N='01';K='RQ1–RQ2';T='Chất lượng AI';D="Text · Image · Hybrid Search`rRAG · memory · phiên dài";P="Ground truth đóng băng`rBaseline · ablation · P95";C=$C.Blue},
        @{X=4.74;N='02';K='RQ3';T='Chức năng & tích hợp';D="Backend · hợp đồng dịch vụ`rMySQL–Qdrant · E2E · fallback";P="Fixture tái lập`rĐối chiếu dữ liệu tại điểm cuối";C=$C.Orange},
        @{X=8.80;N='03';K='RQ4';T='Phi chức năng';D="Hiệu năng · bảo mật · khả dụng`rQuan sát · tương thích";P="Load/soak · fault injection`rSecurity · cross-browser";C=$C.Teal}
    )
    foreach($layer in $testLayers){
        Add-Shape $s $msoShapeRoundedRectangle $layer.X 1.91 3.56 2.55 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $layer.N ($layer.X+0.25) 2.18 0.58 $layer.C $C.Navy 11
        Add-Text $s $layer.K ($layer.X+2.35) 2.22 0.82 0.20 9 $layer.C $true 3 'Aptos' 1 0 | Out-Null
        Add-Text $s $layer.T ($layer.X+0.25) 2.92 3.00 0.34 17 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $layer.D ($layer.X+0.25) 3.35 3.00 0.50 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
        Add-Line $s ($layer.X+0.25) 3.89 ($layer.X+3.29) 3.89 $C.Line 0.8 | Out-Null
        Add-Text $s $layer.P ($layer.X+0.25) 3.99 3.00 0.38 9 $layer.C $true 1 'Aptos' 1 0 | Out-Null
    }
    Add-Text $s 'QUY MÔ ĐÁNH GIÁ AI' 0.68 4.77 2.12 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    $scaleItems=@(
        @{X=0.68;T='TEXT';V='100 query · 2.703 cặp';C=$C.Blue},
        @{X=3.68;T='IMAGE';V='100 SP · 200 ảnh · 2.935 nhãn';C=$C.Orange},
        @{X=6.68;T='HYBRID';V='100 query · 1.627 cặp';C=$C.Teal},
        @{X=9.68;T='RAG';V="80 câu · 120 evidence`r10 phiên · 230 request";C=$C.Red}
    )
    foreach($scale in $scaleItems){
        Add-Shape $s $msoShapeRoundedRectangle $scale.X 5.08 2.72 0.79 $C.Navy2 $C.Line | Out-Null
        Add-Text $s $scale.T ($scale.X+0.18) 5.26 0.88 0.18 8 $scale.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $scale.V ($scale.X+1.00) 5.20 1.52 0.34 9 $C.White $true 3 'Aptos Display' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 6.10 11.96 0.60 $C.Card $C.Line | Out-Null
    Add-Text $s 'MÔI TRƯỜNG CHUNG' 0.92 6.31 1.65 0.18 8 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Snapshot 1.000 sản phẩm · MySQL test · Qdrant collection riêng · Redis · manifest + seed + endpoint + artifact' 2.48 6.23 9.72 0.30 10 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 22 'KIỂM THỬ & ĐÁNH GIÁ'

    # 23 — AI Service evaluation criteria
    $s = $deck.Slides.Add(23, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Tiêu chí đánh giá AI Service' 'Mỗi chỉ số đo một khía cạnh khác nhau' 'Mũi tên ↑ nghĩa là cao hơn tốt hơn; P95 ↓ nghĩa là 95% yêu cầu hoàn tất không quá giá trị này.'
    $criteria=@(
        @{X=0.68;Y=2.00;T='TEXT SEARCH';M="Hit@5 ↑: có kết quả đúng trong Top-5`rNDCG@5 ↑: đúng hơn được xếp cao · MRR ↑: đúng đầu tiên sớm hơn";G='Gate: Hit@5 ≥ 0,95 · NDCG@5 ≥ 0,80';C=$C.Blue},
        @{X=6.80;Y=2.00;T='IMAGE SEARCH';M="Exact Hit ↑: tìm lại đúng sản phẩm nguồn`rNDCG/mAP ↑: chất lượng xếp hạng các sản phẩm tương tự";G='Gate: Exact Hit@5 ≥ 0,95 · NDCG@5 ≥ 0,80';C=$C.Orange},
        @{X=0.68;Y=4.14;T='HYBRID SEARCH';M="Strict Hit@5 ↑: có ứng viên thỏa toàn ý định`rReq-NDCG/RB@5 ↑: xếp hạng đúng và giữ đủ ràng buộc";G='Gate: Strict ≥ 0,90 · NDCG ≥ 0,863 · RB ≥ 0,90 · P95 ≤ 5 s';C=$C.Teal},
        @{X=6.80;Y=4.14;T='RAG + MEMORY';M="Grounding ↑: phát biểu có bằng chứng`rContext P/R ↑: bằng chứng ít nhiễu và không bỏ sót";G='Gate: Grounding ≥ 0,85 · CP ≥ 0,60 · CR ≥ 0,80 · critical 12/12';C=$C.Red}
    )
    foreach($criterion in $criteria){
        Add-Shape $s $msoShapeRoundedRectangle $criterion.X $criterion.Y 5.84 1.78 $C.Card $C.Line | Out-Null
        Add-Shape $s $msoShapeRectangle $criterion.X $criterion.Y 0.09 1.78 $criterion.C | Out-Null
        Add-Text $s $criterion.T ($criterion.X+0.30) ($criterion.Y+0.22) 2.22 0.24 11 $criterion.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $criterion.M ($criterion.X+0.30) ($criterion.Y+0.60) 5.12 0.66 11 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Line $s ($criterion.X+0.30) ($criterion.Y+1.30) ($criterion.X+5.50) ($criterion.Y+1.30) $C.Line 0.8 | Out-Null
        Add-Text $s $criterion.G ($criterion.X+0.30) ($criterion.Y+1.43) 5.12 0.22 9 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    }
    Add-Text $s 'BIÊN ĐO ĐỘ TRỄ' 0.68 6.32 1.76 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Client end-to-end: gửi request → đọc body → giải mã JSON; không so trực tiếp các workload khác nhau.' 2.38 6.23 9.90 0.36 12 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 23 'KIỂM THỬ & ĐÁNH GIÁ'

    # 24 — Baseline and comparison design
    $s = $deck.Slides.Add(24, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Thiết kế so sánh' 'Baseline và ablation giúp chọn cấu hình bằng bằng chứng' 'Mỗi phép so sánh giữ cố định dữ liệu và điều kiện; chỉ thay thành phần cần kiểm chứng.'
    $comparisons=@(
        @{X=0.68;Y=2.00;N='01';T='Text Search';D='BM25  ↔  Vector no-rerank  ↔  Vector + rerank';S='Cùng 100 truy vấn · đo chất lượng và P95';C=$C.Blue},
        @{X=6.80;Y=2.00;N='02';T='Image Search';D='Ảnh catalog  ↔  ảnh bên ngoài challenging';S='Cùng 100 sản phẩm, embedding, index và Top-20';C=$C.Orange},
        @{X=0.68;Y=4.10;N='03';T='Hybrid Search';D='Image-only · Text-only · post-filter · fusion ± rerank';S='Cùng 100 truy vấn · 1.627 cặp duyệt thủ công';C=$C.Teal},
        @{X=6.80;Y=4.10;N='04';T='Conversational AI';D='LLM-only  →  +RAG  →  +memory  →  +rerank';S='Cùng 80 câu hỏi · 12 ca critical hard gate';C=$C.Red}
    )
    foreach($cmp in $comparisons){
        Add-Shape $s $msoShapeRoundedRectangle $cmp.X $cmp.Y 5.84 1.66 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $cmp.N ($cmp.X+0.28) ($cmp.Y+0.28) 0.58 $cmp.C $C.Navy 11
        Add-Text $s $cmp.T ($cmp.X+1.08) ($cmp.Y+0.22) 2.34 0.32 16 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $cmp.D ($cmp.X+1.08) ($cmp.Y+0.67) 4.38 0.38 11 $cmp.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $cmp.S ($cmp.X+1.08) ($cmp.Y+1.17) 4.38 0.25 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 6.14 11.96 0.62 $C.Teal $C.Teal | Out-Null
    Add-Text $s 'NGUYÊN TẮC CHỌN' 0.95 6.35 1.76 0.20 9 $C.TealDark $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Ưu tiên cấu hình đạt gate, chất lượng tốt hơn và độ trễ thấp hơn — không mặc định mô hình phức tạp hơn sẽ tốt hơn.' 2.72 6.27 9.38 0.32 12 $C.Navy $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 24 'KIỂM THỬ & ĐÁNH GIÁ'

    # 25 — Baseline versus proposed results
    $s = $deck.Slides.Add(25, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Kết quả so sánh baseline' 'Cấu hình được chọn từ chênh lệch đo trên cùng tập truy vấn' 'Δ = cấu hình bên phải trừ baseline; dấu âm ở hàng cuối giải thích vì sao rerank bị tắt.'
    $cols=@(0.68,3.25,5.43,6.93,8.43,9.83);$widths=@(2.51,2.12,1.44,1.44,1.34,2.81)
    $heads=@('Phép so sánh','Chỉ số','Baseline','Đề xuất','Δ','Quyết định')
    for($i=0;$i -lt 6;$i++){Add-Shape $s $msoShapeRectangle $cols[$i] 1.93 $widths[$i] 0.55 $C.Card $C.Line|Out-Null;Add-Text $s $heads[$i] ($cols[$i]+0.08) 2.09 ($widths[$i]-0.16) 0.20 9 $C.Muted $true $(if($i -lt 2){1}else{2}) 'Aptos' 1 0|Out-Null}
    $comparative=@(
        @('Text: BM25 → Vector','Hit@5','0,756','1,000','+0,244','Chọn Vector no-rerank'),
        @('Text: BM25 → Vector','NDCG@5','0,689','0,941','+0,252','Xếp hạng tốt hơn'),
        @('Hybrid: Fusion → Image-cond.','Strict Hit@5','0,920','0,980','+0,060','Chọn Image-conditioned'),
        @('Hybrid: no-rerank → rerank','Strict Hit@5','0,980','0,730','−0,250','Tắt rerank')
    )
    $cy=2.48
    for($r=0;$r -lt $comparative.Count;$r++){
        $row=$comparative[$r];$deltaColor=if($r -eq 3){$C.Red}else{$C.Teal}
        for($i=0;$i -lt 6;$i++){Add-Shape $s $msoShapeRectangle $cols[$i] $cy $widths[$i] 0.72 $(if($r%2 -eq 0){$C.Navy2}else{$C.Card}) $C.Line|Out-Null}
        Add-Text $s $row[0] 0.84 ($cy+0.20) 2.20 0.27 10 $C.White $true 1 'Aptos' 1 0|Out-Null
        Add-Text $s $row[1] 3.39 ($cy+0.20) 1.82 0.27 10 $C.Muted $true 1 'Aptos' 1 0|Out-Null
        Add-Text $s $row[2] 5.51 ($cy+0.18) 1.28 0.30 13 $C.Muted $true 2 'Aptos Display' 1 0|Out-Null
        Add-Text $s $row[3] 7.01 ($cy+0.18) 1.28 0.30 13 $C.White $true 2 'Aptos Display' 1 0|Out-Null
        Add-Text $s $row[4] 8.51 ($cy+0.18) 1.18 0.30 13 $deltaColor $true 2 'Aptos Display' 1 0|Out-Null
        Add-Text $s $row[5] 10.00 ($cy+0.19) 2.44 0.28 10 $deltaColor $true 1 'Aptos' 1 0|Out-Null
        $cy+=0.72
    }
    $other=@(
        @{X=0.68;T='IMAGE — ẢNH NGOÀI';V='Exact Hit@5 0,970';D='NDCG@5 0,810 · giảm 0,043 so với ảnh catalog';C=$C.Orange},
        @{X=6.78;T='RAG + MEMORY';V='Grounding 0,824 → 1,000';D='Critical 4/12 → 12/12 · Context P/R đạt 0,946 / 0,944';C=$C.Teal}
    )
    foreach($o in $other){Add-Shape $s $msoShapeRoundedRectangle $o.X 5.62 5.86 0.92 $C.Card $o.C|Out-Null;Add-Text $s $o.T ($o.X+0.23) 5.82 1.82 0.20 9 $o.C $true 1 'Aptos' 1 0|Out-Null;Add-Text $s $o.V ($o.X+2.02) 5.75 3.52 0.28 15 $C.White $true 1 'Aptos Display' 1 0|Out-Null;Add-Text $s $o.D ($o.X+0.23) 6.15 5.18 0.22 8 $C.Muted $false 1 'Aptos' 1 0|Out-Null}
    Add-Footer $s 25 'KIỂM THỬ & ĐÁNH GIÁ'

    # 26 — API and integration testing
    $s = $deck.Slides.Add(26, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Kiểm thử API & tích hợp' 'Kiểm tra tại ranh giới nơi dữ liệu có thể mất nhất quán' 'Không chỉ kiểm HTTP 200: kết quả được đối chiếu lại ở MySQL, Qdrant và log theo request.'
    $apiStats=@(
        @{X=0.68;V='26';T='Spring Controllers';D='126 request mappings';C=$C.Blue},
        @{X=3.74;V='14';T='FastAPI endpoints';D='Search · chat · index · health';C=$C.Teal},
        @{X=6.80;V='1.000';T='product_id';D='Đủ trên hai collection';C=$C.Orange},
        @{X=9.86;V='8/8';T='URL ảnh hồi quy';D='product_id = 648';C=$C.Red}
    )
    foreach($a in $apiStats){
        Add-Shape $s $msoShapeRoundedRectangle $a.X 2.00 2.78 1.18 $C.Card $C.Line | Out-Null
        Add-Text $s $a.V ($a.X+0.22) 2.22 1.00 0.39 22 $a.C $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $a.T ($a.X+1.15) 2.20 1.38 0.28 11 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $a.D ($a.X+1.15) 2.65 1.38 0.22 8 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 3.59 11.96 1.38 $C.Card $C.Line | Out-Null
    $flowNames=@('Frontend','Spring Boot','AI Service','Qdrant','MySQL xác nhận')
    $flowColors=@($C.Blue,$C.Orange,$C.Teal,$C.Blue,$C.Orange)
    $ix=0.99
    for($i=0;$i -lt $flowNames.Count;$i++){
        Add-Shape $s $msoShapeRoundedRectangle $ix 3.97 1.72 0.62 $C.Navy2 $flowColors[$i] | Out-Null
        Add-Text $s $flowNames[$i] ($ix+0.10) 4.15 1.52 0.22 10 $C.White $true 2 'Aptos' 1 0 | Out-Null
        if($i -lt 4){ Add-Text $s '→' ($ix+1.74) 4.08 0.43 0.30 15 $C.Line $true 2 'Aptos' 1 0 | Out-Null }
        $ix += 2.25
    }
    $checks=@(
        @{X=0.68;T='Hợp đồng';D='Schema request/response, API key, lỗi chuẩn hóa';C=$C.Blue},
        @{X=3.74;T='Đồng bộ';D='Full/incremental sync, retry, snapshot, alias rollback';C=$C.Teal},
        @{X=6.80;T='Suy giảm';D='AI lỗi: catalog, cart và order vẫn hoạt động';C=$C.Orange},
        @{X=9.86;T='Quan sát';D='X-Correlation-ID đi xuyên Backend → AI';C=$C.Red}
    )
    foreach($check in $checks){
        Add-Shape $s $msoShapeRoundedRectangle $check.X 5.35 2.78 1.08 $C.Navy2 $C.Line | Out-Null
        Add-Text $s $check.T ($check.X+0.22) 5.57 1.20 0.26 13 $check.C $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $check.D ($check.X+0.22) 5.94 2.28 0.31 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Footer $s 26 'KIỂM THỬ & ĐÁNH GIÁ'

    # 27 — Performance, security, compatibility
    $s = $deck.Slides.Add(27, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Hiệu năng, bảo mật & tương thích' 'Đạt các gate đã chạy — đồng thời giữ rõ giới hạn đánh giá' 'Số liệu đại diện cho môi trường thử nghiệm, không được suy rộng thành production.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 2.00 3.80 4.47 $C.Card $C.Blue | Out-Null
    Add-Text $s 'HIỆU NĂNG' 0.98 2.30 1.42 0.22 10 $C.Blue $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s '182,79 ms' 0.98 2.78 2.72 0.55 27 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'P95 tải hỗn hợp Catalog–Cart' 0.98 3.34 2.95 0.28 10 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 0.98 3.82 4.15 3.82 $C.Line 1 | Out-Null
    Add-Text $s '57.600 / 57.600' 0.98 4.08 2.55 0.34 18 $C.Blue $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'request soak 2 giờ · 0 lỗi' 0.98 4.47 2.74 0.25 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'P95 soak 48,863 ms' 0.98 5.08 2.86 0.30 13 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'AI 360/360 · P95 tối đa 2,776 giây' 0.98 5.68 3.05 0.34 8 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Text / Hybrid / Assistant: 1,412 / 0,516 / 2,776 giây' 0.98 5.98 3.10 0.34 7 $C.Muted $false 1 'Aptos' 1 0 | Out-Null

    Add-Shape $s $msoShapeRoundedRectangle 4.76 2.00 3.80 4.47 $C.Card $C.Red | Out-Null
    Add-Text $s 'BẢO MẬT' 5.06 2.30 1.42 0.22 10 $C.Red $true 1 'Aptos' 1 0 | Out-Null
    $security=@('JWT · RBAC · CORS · IDOR','Injection · XSS · path traversal','Rate limit → HTTP 429','Upload quá cỡ → HTTP 413','npm audit production: 0 lỗ hổng')
    $sy=2.86
    foreach($item in $security){
        Add-CircleLabel $s '✓' 5.06 $sy 0.30 $C.Teal $C.Navy 10
        Add-Text $s $item 5.52 ($sy+0.03) 2.50 0.30 10 $C.White $true 1 'Aptos' 1 0 | Out-Null
        $sy += 0.56
    }
    Add-Text $s 'Chưa thay thế pentest độc lập' 5.06 5.81 2.70 0.27 9 $C.Orange $true 1 'Aptos' 1 0 | Out-Null

    Add-Shape $s $msoShapeRoundedRectangle 8.84 2.00 3.80 4.47 $C.Card $C.Teal | Out-Null
    Add-Text $s 'TƯƠNG THÍCH' 9.14 2.30 2.16 0.22 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s '8 / 8' 9.14 2.80 1.56 0.55 27 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Playwright Firefox / WebKit' 9.14 3.35 2.65 0.28 10 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 9.14 3.82 12.31 3.82 $C.Line 1 | Out-Null
    Add-Text $s 'Desktop + mobile' 9.14 4.10 2.42 0.29 15 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Chrome · Edge · Firefox · WebKit' 9.14 4.54 2.82 0.25 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Build & lint: đạt' 9.14 5.08 2.42 0.29 13 $C.Teal $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Chưa có Safari thật / SUS người dùng' 9.14 5.81 2.92 0.27 9 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Footer $s 27 'KIỂM THỬ & ĐÁNH GIÁ'

    # 28 — Test summary
    $s = $deck.Slides.Add(28, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Tổng hợp kết quả kiểm thử' 'Kết luận theo phạm vi bằng chứng' 'Trạng thái “Đạt” và “Đạt có giới hạn” phản ánh đúng phạm vi kiểm chứng.'
    $status=@(
        @{X=0.68;Y=2.00;T='Text Search';S='ĐẠT';D='Hit@5 1,000 · vượt BM25';C=$C.Teal},
        @{X=4.74;Y=2.00;T='Image Search';S='ĐẠT CÓ GIỚI HẠN';D='Challenging Exact Hit@5 0,970';C=$C.Orange},
        @{X=8.80;Y=2.00;T='Hybrid Search';S='ĐẠT';D='Strict 0,980 · Req-NDCG 0,958 · RB 0,990';C=$C.Teal},
        @{X=0.68;Y=3.43;T='RAG & Memory';S='ĐẠT';D='Grounding 1,000 · critical 12/12';C=$C.Teal},
        @{X=4.74;Y=3.43;T='Nghiệp vụ & tích hợp';S='ĐẠT';D='102/102 · sync · E2E · fallback';C=$C.Teal},
        @{X=8.80;Y=3.43;T='Phi chức năng';S='ĐẠT TRONG PHẠM VI';D='Load · security · health · browser';C=$C.Blue}
    )
    foreach($st in $status){
        Add-Shape $s $msoShapeRoundedRectangle $st.X $st.Y 3.56 1.16 $C.Card $C.Line | Out-Null
        Add-Text $s $st.T ($st.X+0.24) ($st.Y+0.20) 1.90 0.25 13 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $st.S ($st.X+2.05) ($st.Y+0.22) 1.16 0.20 8 $st.C $true 3 'Aptos' 1 0 | Out-Null
        Add-Line $s ($st.X+0.24) ($st.Y+0.56) ($st.X+3.25) ($st.Y+0.56) $C.Line 1 | Out-Null
        Add-Text $s $st.D ($st.X+0.24) ($st.Y+0.73) 2.98 0.24 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 5.17 11.96 1.20 $C.Teal $C.Teal | Out-Null
    Add-Text $s 'KẾT LUẬN KIỂM THỬ' 0.98 5.45 2.12 0.22 10 $C.TealDark $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Hệ thống đạt tiêu chí nghiệm thu nội bộ trong phạm vi đồ án.' 3.00 5.35 8.92 0.38 18 $C.Navy $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Kết quả chưa phải chứng nhận sẵn sàng vận hành thương mại quy mô lớn.' 3.00 5.84 8.94 0.26 10 $C.TealDark $true 1 'Aptos' 1 0 | Out-Null
    Add-Footer $s 28 'KIỂM THỬ & ĐÁNH GIÁ'

    # 29 — Conclusion: completed outcomes
    $s = $deck.Slides.Add(29, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Kết luận' 'Đề tài đã hoàn thành các mục tiêu đặt ra' 'Một hệ thống thương mại điện tử thời trang tích hợp trợ lý mua sắm đa phương thức.'
    $completed=@(
        @{X=0.68;Y=1.96;N='01';T='Sản phẩm thương mại điện tử';D="Khách hàng: tài khoản · khám phá · giỏ hàng · COD`rQuản trị: sản phẩm · tồn kho · đơn hàng · nội dung";C=$C.Blue},
        @{X=6.78;Y=1.96;N='02';T='Năng lực AI đa phương thức';D="Text · Image · Hybrid Search · YOLOv26`rRAG có căn cứ · bộ nhớ hội thoại nhiều lượt";C=$C.Teal},
        @{X=0.68;Y=4.10;N='03';T='Kiến trúc & triển khai';D="React · Spring Boot · FastAPI · MySQL · Qdrant`rDocker · local · Google Cloud · fallback khi AI lỗi";C=$C.Orange},
        @{X=6.78;Y=4.10;N='04';T='Kiểm thử & đánh giá';D="AI đạt các gate · Backend 102/102 ca`r5 luồng E2E · đồng bộ đủ 1.000 product_id";C=$C.Red}
    )
    foreach($item in $completed){
        Add-Shape $s $msoShapeRoundedRectangle $item.X $item.Y 5.86 1.72 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $item.N ($item.X+0.27) ($item.Y+0.34) 0.64 $item.C $C.Navy 12
        Add-Text $s $item.T ($item.X+1.16) ($item.Y+0.25) 4.28 0.34 17 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $item.D ($item.X+1.16) ($item.Y+0.76) 4.30 0.62 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 6.18 11.96 0.56 $C.Teal $C.Teal | Out-Null
    Add-Text $s 'KẾT QUẢ' 0.95 6.37 1.02 0.18 9 $C.TealDark $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Kết hợp được các chức năng mua sắm chính với tìm kiếm đa phương thức và trợ lý hội thoại.' 1.95 6.28 10.20 0.30 12 $C.Navy $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 29 'KẾT LUẬN'

    # 30 — Future development
    $s = $deck.Slides.Add(30, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Hướng phát triển' 'Mở rộng từ nguyên mẫu đến hệ thống có thể phục vụ thực tế' 'Ưu tiên dữ liệu và chất lượng tìm kiếm trước, sau đó củng cố vận hành và trải nghiệm.'
    $future=@(
        @{X=0.68;Y=1.95;N='01';T='Mở rộng dữ liệu';D='Thêm sản phẩm, ngành hàng, truy vấn và ảnh thực tế; tách tập điều chỉnh với tập đánh giá.';C=$C.Blue},
        @{X=4.74;Y=1.95;N='02';T='Cải thiện tìm kiếm';D='Hiểu sâu màu, giá, loại, mục đích; tách nền và nhận diện vật thể tốt hơn.';C=$C.Orange},
        @{X=8.80;Y=1.95;N='03';T='Cá nhân hóa';D='Khai thác lịch sử, lượt xem, yêu thích và đơn hàng; cho phép người dùng kiểm soát dữ liệu.';C=$C.Teal},
        @{X=0.68;Y=3.86;N='04';T='Hoàn thiện mua sắm';D='Thanh toán trực tuyến, vận chuyển, theo dõi, đổi trả, ứng dụng di động và thông báo.';C=$C.Red},
        @{X=4.74;Y=3.86;N='05';T='Tăng khả năng phục vụ';D='Tải dài hơn, autoscale, hàng đợi đồng bộ và bản sao dữ liệu để giảm gián đoạn.';C=$C.Blue},
        @{X=8.80;Y=3.86;N='06';T='An toàn & trải nghiệm';D='Pentest, diễn tập khôi phục, dashboard vận hành và đánh giá với người dùng thực.';C=$C.Orange}
    )
    foreach($item in $future){
        Add-Shape $s $msoShapeRoundedRectangle $item.X $item.Y 3.56 1.54 $C.Card $C.Line | Out-Null
        Add-CircleLabel $s $item.N ($item.X+0.22) ($item.Y+0.25) 0.54 $item.C $C.Navy 10
        Add-Text $s $item.T ($item.X+0.94) ($item.Y+0.20) 2.26 0.32 14 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $item.D ($item.X+0.22) ($item.Y+0.83) 3.06 0.48 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 5.78 11.96 0.76 $C.Navy2 $C.Teal | Out-Null
    Add-Text $s 'ƯU TIÊN TRƯỚC MẮT' 0.96 6.04 1.85 0.19 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Mở rộng dữ liệu đánh giá  →  cải thiện tìm kiếm kết hợp  →  tải dài  →  bảo mật & quan sát' 2.76 5.95 9.34 0.34 12 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Footer $s 30 'HƯỚNG PHÁT TRIỂN'

    # 31 — Q&A
    $s = $deck.Slides.Add(31, $ppLayoutBlank)
    Add-Background $s
    Add-Text $s 'TRAO ĐỔI' 0.68 0.58 2.20 0.24 11 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Q & A' 0.65 1.24 5.12 0.94 46 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'Cảm ơn Hội đồng đã lắng nghe.' 0.68 2.16 6.20 0.45 20 $C.Teal $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 0.68 3.15 11.96 2.06 $C.Card $C.Line | Out-Null
    $qa=@(
        @{X=1.95;N='01';T='Bài toán';D='Nhu cầu · phạm vi · điểm khác biệt';C=$C.Blue},
        @{X=5.05;N='02';T='Kỹ thuật';D='Kiến trúc · RAG · multimodal';C=$C.Orange},
        @{X=8.15;N='03';T='Bằng chứng';D='Ground truth · baseline · latency';C=$C.Teal},
        @{X=11.25;N='04';T='Giới hạn';D='Rủi ro · hướng phát triển';C=$C.Red}
    )
    foreach($q in $qa){Add-CircleLabel $s $q.N ($q.X-0.29) 3.55 0.58 $q.C $C.Navy 11;Add-Text $s $q.T ($q.X-1.18) 4.30 2.36 0.30 14 $C.White $true 2 'Aptos Display' 1 0|Out-Null;Add-Text $s $q.D ($q.X-1.24) 4.70 2.48 0.42 9 $C.Muted $false 2 'Aptos' 1 0|Out-Null}
    Add-Text $s 'Huỳnh Thái Minh Châu · 2210352' 0.68 6.25 7.55 0.27 10 $C.Gray $false 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'GVHD: ThS. Võ Thanh Hùng' 8.80 6.25 3.55 0.27 10 $C.Gray $false 3 'Aptos' 1 0 | Out-Null
    Add-Footer $s 31 'Q&A'

    # 32 — References
    $s = $deck.Slides.Add(32, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Tài liệu tham khảo' 'Nguồn cho bối cảnh, giải pháp liên quan và phương pháp' 'Các liên kết màu xanh có thể mở trực tiếp; số liệu nội bộ được truy vết trong repository.'
    $refs=@(
        @{Y=1.80;N='[1]';T='Google (2024). 3 ways visual search helps you shop.';L='blog.google — Google Lens';U='https://blog.google/products-and-platforms/products/shopping/visual-search-lens-shopping/';C=$C.Blue},
        @{Y=2.38;N='[2]';T='Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.';L='arXiv:2005.11401';U='https://arxiv.org/abs/2005.11401';C=$C.Teal},
        @{Y=2.96;N='[3]';T='Radford et al. (2021). Learning Transferable Visual Models From Natural Language Supervision.';L='arXiv:2103.00020';U='https://arxiv.org/abs/2103.00020';C=$C.Orange},
        @{Y=3.54;N='[4]';T='Shopee Việt Nam. Cách tìm kiếm sản phẩm cần mua trên Shopee.';L='help.shopee.vn';U='https://help.shopee.vn/portal/4/article/79283';C=$C.Orange},
        @{Y=4.12;N='[5]';T='Tiki. Tổng hợp các tính năng hỗ trợ Nhà Bán.';L='hocvien.tiki.vn';U='https://hocvien.tiki.vn/faq/tong-hop-cac-tinh-nang-ho-tro-nha-ban/';C=$C.Blue},
        @{Y=4.70;N='[6]';T='Google (2022). Go Beyond the Search Box: Introducing Multisearch.';L='blog.google — Multisearch';U='https://blog.google/products-and-platforms/products/search/multisearch/';C=$C.Teal}
    )
    foreach($ref in $refs){
        Add-Shape $s $msoShapeRoundedRectangle 0.68 $ref.Y 11.96 0.48 $C.Card $C.Line | Out-Null
        Add-Text $s $ref.N 0.92 ($ref.Y+0.12) 0.54 0.18 9 $ref.C $true 1 'Aptos' 1 0 | Out-Null
        $refLink=Add-Text $s $ref.T 1.45 ($ref.Y+0.10) 7.10 0.22 9 $C.White $true 1 'Aptos' 1 0
        $refLink.ActionSettings(1).Hyperlink.Address=$ref.U
        $urlLink=Add-Text $s $ref.L 8.60 ($ref.Y+0.11) 3.62 0.20 8 $ref.C $false 3 'Consolas' 1 0
        $urlLink.ActionSettings(1).Hyperlink.Address=$ref.U
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 5.48 11.96 0.70 $C.Navy2 $C.Line | Out-Null
    Add-Text $s 'NGUỒN NỘI BỘ' 0.95 5.72 1.42 0.20 9 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'report-datn/Sections/02-PhanTichYeuCau.tex · 07-KiemThuHeThong.tex · evals/' 2.27 5.64 9.88 0.30 9 $C.White $true 1 'Consolas' 1 0 | Out-Null
    Add-Footer $s 32 'TÀI LIỆU THAM KHẢO'

    # A1 — Detailed test matrix
    $s = $deck.Slides.Add(33, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Phụ lục A1' 'Ma trận kiểm thử chi tiết' 'Quy mô, chỉ số chính và bằng chứng được lưu theo từng nhóm.'
    $cols=@(0.68,3.02,5.00,8.23,10.76);$widths=@(2.28,1.92,3.17,2.47,1.88)
    $heads=@('Nhóm','Quy mô','Chỉ số / gate','Kết quả chính','Trạng thái')
    for($i=0;$i -lt 5;$i++){Add-Shape $s $msoShapeRectangle $cols[$i] 1.93 $widths[$i] 0.58 $C.Card $C.Line|Out-Null;Add-Text $s $heads[$i] ($cols[$i]+0.10) 2.10 ($widths[$i]-0.20) 0.20 9 $C.Muted $true $(if($i -eq 0){1}else{2}) 'Aptos' 1 0|Out-Null}
    $matrix=@(
        @('Text Search','100 query','Hit@5 · NDCG · MRR','1,000 · 0,941 · 0,963','Đạt'),
        @('Image Search','100 cặp / 200 ảnh','Exact Hit@5 · NDCG','1,000/0,970 · 0,853/0,810','Có giới hạn'),
        @('Hybrid Search','100 query / 1.627 cặp','Strict · Req-NDCG · RB','0,980 · 0,958 · 0,990','Đạt'),
        @('RAG & Memory','80 + 230 req','Grounding · context · critical','1,000 · 0,946/0,944 · 12/12','Đạt'),
        @('Backend / E2E','102 ca + hành trình','Data · auth · transaction','102/102 · E2E đạt','Đạt'),
        @('Phi chức năng','6.050 + 57.600 + 360','Backend · soak · AI','0 lỗi · 48,863 ms · P95 max 2,776 s','Trong phạm vi')
    )
    $my=2.51
    foreach($row in $matrix){
        for($i=0;$i -lt 5;$i++){
            $fill=if($row[4] -eq 'Đạt' -and $i -eq 4){$C.Teal}elseif($row[4] -eq 'Một phần' -and $i -eq 4){$C.Red}elseif($i -eq 4){$C.Navy2}else{$C.Card}
            Add-Shape $s $msoShapeRectangle $cols[$i] $my $widths[$i] 0.67 $fill $C.Line|Out-Null
            $tc=if($i -eq 4 -and $row[4] -eq 'Đạt'){$C.Navy}elseif($i -eq 4 -and $row[4] -eq 'Một phần'){$C.White}else{$C.Muted}
            Add-Text $s $row[$i] ($cols[$i]+0.10) ($my+0.17) ($widths[$i]-0.20) 0.30 9 $tc $(if($i -eq 0 -or $i -eq 4){$true}else{$false}) $(if($i -eq 0){1}else{2}) 'Aptos' 1 0|Out-Null
        }
        $my+=0.67
    }
    Add-Text $s 'Nguồn: report-datn/Sections/07-KiemThuHeThong.tex và các artifact trong evals/, report-datn/Evidence/.' 0.70 6.70 11.70 0.22 8 $C.Gray $false 1 'Aptos' 1 0 | Out-Null
    Add-AppendixFooter $s 'A1 / A6'

    # A2 — Detailed performance results
    $s = $deck.Slides.Add(34, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Phụ lục A2' 'Kết quả hiệu năng chi tiết' 'Backend 6.050 request · soak 2 giờ 57.600 request · tải AI đại diện 360 request.'
    Add-Text $s 'P95 TRƯỚC / SAU TỐI ƯU' 0.68 2.02 2.40 0.22 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Trước' 0.68 2.62 0.66 0.22 10 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 1.42 2.52 6.65 0.46 $C.Red $C.Red | Out-Null
    Add-Text $s '693,46 ms' 7.12 2.58 1.20 0.22 10 $C.White $true 3 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Sau' 0.68 3.34 0.66 0.22 10 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 1.42 3.24 1.75 0.46 $C.Teal $C.Teal | Out-Null
    Add-Text $s '182,79 ms' 3.28 3.30 1.20 0.22 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 6.22 2.32 6.22 3.96 $C.Orange 1.5 | Out-Null
    Add-Text $s 'Gate 500 ms' 5.44 4.00 1.56 0.20 9 $C.Orange $true 2 'Aptos' 1 0 | Out-Null
    Add-Shape $s $msoShapeRoundedRectangle 8.63 2.02 4.01 2.23 $C.Card $C.Line | Out-Null
    Add-Text $s '−73,6%' 8.96 2.45 2.42 0.55 28 $C.Teal $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'P95 sau tối ưu cache, cart và chỉ mục giá' 8.96 3.19 2.98 0.52 11 $C.White $true 1 'Aptos' 1 0 | Out-Null
    $perf=@(
        @{X=0.68;V='93,05';T='P50 (ms)';C=$C.Blue},@{X=3.18;V='182,79';T='P95 (ms)';C=$C.Teal},
        @{X=5.68;V='266,76';T='P99 (ms)';C=$C.Orange},@{X=8.18;V='19,999';T='request / giây';C=$C.Red},
        @{X=10.68;V='0';T='request lỗi';C=$C.Teal}
    )
    foreach($p in $perf){Add-Shape $s $msoShapeRoundedRectangle $p.X 4.73 2.10 1.20 $C.Card $C.Line|Out-Null;Add-Text $s $p.V ($p.X+0.18) 4.98 1.74 0.36 20 $p.C $true 2 'Aptos Display' 1 0|Out-Null;Add-Text $s $p.T ($p.X+0.18) 5.49 1.74 0.23 9 $C.Muted $false 2 'Aptos' 1 0|Out-Null}
    Add-Text $s 'KẾT QUẢ BỔ SUNG' 0.68 6.35 1.58 0.20 9 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Soak: P95 48,863 ms · heap +8,210 MiB  |  AI P95 Text / Hybrid / Assistant: 1,412 / 0,516 / 2,776 giây.' 2.26 6.25 9.84 0.40 10 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-AppendixFooter $s 'A2 / A6'

    # A3 — API list
    $s = $deck.Slides.Add(35, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Phụ lục A3' 'Danh sách API theo miền trách nhiệm' 'Spring Boot công khai nghiệp vụ; FastAPI chỉ phục vụ AI và vận hành nội bộ.'
    Add-Shape $s $msoShapeRoundedRectangle 0.68 1.96 7.34 4.68 $C.Card $C.Blue | Out-Null
    Add-Text $s 'SPRING BOOT API' 0.98 2.27 2.08 0.22 10 $C.Blue $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s '26 controllers  ·  126 request mappings' 0.98 2.67 5.20 0.33 17 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    $apiGroups=@(
        @{Y=3.30;T='Khách hàng';D='Auth · Me · Catalog · Cart · Checkout · Order · Wishlist · Review · Blog';C=$C.Teal},
        @{Y=4.15;T='Quản trị';D='Catalog · Inventory · Order · Payment · Promotion · Coupon · Customer · Blog · AI Sync';C=$C.Orange},
        @{Y=5.00;T='AI Gateway';D='AiSearch · AiAssistant · InternalAiProduct';C=$C.Red},
        @{Y=5.85;T='Hợp đồng';D='JSON · JWT/RBAC · internal API key · lỗi API thống nhất';C=$C.Blue}
    )
    foreach($g in $apiGroups){Add-Shape $s $msoShapeRoundedRectangle 0.98 $g.Y 6.72 0.64 $C.Navy2 $C.Line|Out-Null;Add-Text $s $g.T 1.18 ($g.Y+0.17) 1.10 0.22 10 $g.C $true 1 'Aptos' 1 0|Out-Null;Add-Text $s $g.D 2.38 ($g.Y+0.15) 4.98 0.28 9 $C.Muted $false 1 'Aptos' 1 0|Out-Null}
    Add-Shape $s $msoShapeRoundedRectangle 8.32 1.96 4.32 4.68 $C.Card $C.Teal | Out-Null
    Add-Text $s 'FASTAPI — 14 ENDPOINTS' 8.62 2.27 2.86 0.22 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    $fast=@(
        @{N='05';T='Search';D='/text · /image · /hybrid · /auto · detections';C=$C.Blue},
        @{N='01';T='Assistant';D='/chat';C=$C.Teal},
        @{N='04';T='Indexing';D='batch · product · delete · reindex';C=$C.Orange},
        @{N='04';T='Operations';D='health · ready · capability · metrics';C=$C.Red}
    )
    $fy=2.85
    foreach($f in $fast){Add-CircleLabel $s $f.N 8.65 $fy 0.50 $f.C $C.Navy 10;Add-Text $s $f.T 9.38 ($fy+0.01) 1.18 0.26 13 $C.White $true 1 'Aptos Display' 1 0|Out-Null;Add-Text $s $f.D 9.38 ($fy+0.35) 2.74 0.29 9 $C.Muted $false 1 'Aptos' 1 0|Out-Null;$fy+=0.86}
    Add-AppendixFooter $s 'A3 / A6'

    # A4 — Defects discovered and fixed
    $s = $deck.Slides.Add(36, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Phụ lục A4' 'Các lỗi đã phát hiện và khắc phục' 'Kiểm thử được dùng để thay đổi thiết kế, không chỉ xác nhận kết quả cuối.'
    $fixes=@(
        @{Y=1.98;Issue='P95 tải hỗn hợp 693,46 ms';Fix='Cache catalog + bỏ đọc giỏ dư + index giá mới nhất';Proof='182,79 ms';C=$C.Blue},
        @{Y=2.75;Issue='White / Ecru / Ivory lệch khóa';Fix='Canonical color + ưu tiên màu catalog gốc';Proof='E2E 5/5';C=$C.Teal},
        @{Y=3.52;Issue='Rerank làm giảm NDCG / Hit@5';Fix='Tắt rerank theo ablation; giữ adapter để thử lại';Proof='Hybrid Strict 0,980 → 0,730';C=$C.Orange},
        @{Y=4.29;Issue='URL ảnh master.m3u8 sai payload';Fix='Chuẩn hóa media URL khi đồng bộ';Proof='8/8 URL';C=$C.Red},
        @{Y=5.06;Issue='SMTP lỗi kéo health tổng xuống';Fix='Tách mail khỏi liveness/readiness';Proof='3/3 + 102/102';C=$C.Blue},
        @{Y=5.83;Issue='Upload lớn / spam auth trả lỗi chưa đúng';Fix='HTTP 413 + rate limit 10/60s trả 429';Proof='Regression đạt';C=$C.Teal}
    )
    Add-Text $s 'PHÁT HIỆN' 0.96 1.68 2.42 0.20 9 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'KHẮC PHỤC' 4.61 1.68 3.04 0.20 9 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'BẰNG CHỨNG' 10.17 1.68 1.75 0.20 9 $C.Muted $true 1 'Aptos' 1 0 | Out-Null
    foreach($f in $fixes){
        Add-Shape $s $msoShapeRoundedRectangle 0.68 $f.Y 11.96 0.63 $C.Card $C.Line | Out-Null
        Add-Shape $s $msoShapeRectangle 0.68 $f.Y 0.08 0.63 $f.C | Out-Null
        Add-Text $s $f.Issue 0.95 ($f.Y+0.16) 3.30 0.28 10 $C.White $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s '→' 4.26 ($f.Y+0.15) 0.30 0.28 13 $C.Line $true 2 'Aptos' 1 0 | Out-Null
        Add-Text $s $f.Fix 4.62 ($f.Y+0.15) 5.12 0.30 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $f.Proof 10.12 ($f.Y+0.15) 2.10 0.28 10 $f.C $true 2 'Aptos' 1 0 | Out-Null
    }
    Add-AppendixFooter $s 'A4 / A6'

    # A5 — YOLOv26 fine-tuning results
    $s = $deck.Slides.Add(37, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Phụ lục A5' 'Kết quả fine-tune YOLOv26s' 'Mô hình được dùng để phát hiện và crop vùng sản phẩm trước khi tạo image embedding.'
    $yoloMetrics=@(
        @{X=0.68;T='PRECISION';V='0,875';C=$C.Blue},
        @{X=3.74;T='RECALL';V='0,760';C=$C.Orange},
        @{X=6.80;T='mAP50';V='0,849';C=$C.Teal},
        @{X=9.86;T='mAP50–95';V='0,685';C=$C.Red}
    )
    foreach($metric in $yoloMetrics){
        Add-Shape $s $msoShapeRoundedRectangle $metric.X 1.92 2.78 1.12 $C.Card $C.Line | Out-Null
        Add-Text $s $metric.T ($metric.X+0.22) 2.15 1.30 0.22 9 $metric.C $true 1 'Aptos' 1 0 | Out-Null
        Add-Text $s $metric.V ($metric.X+1.27) 2.10 1.25 0.38 21 $C.White $true 3 'Aptos Display' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 3.36 7.44 2.80 $C.Card $C.Line | Out-Null
    Add-Text $s 'mAP50 THEO LỚP' 0.98 3.65 2.20 0.22 10 $C.Teal $true 1 'Aptos' 1 0 | Out-Null
    $classMetrics=@(
        @{Y=4.18;T='Clothing';V=0.947;S='0,947';C=$C.Teal},
        @{Y=4.66;T='Shoes';V=0.945;S='0,945';C=$C.Blue},
        @{Y=5.14;T='Bags';V=0.807;S='0,807';C=$C.Orange},
        @{Y=5.62;T='Accessories';V=0.695;S='0,695';C=$C.Red}
    )
    foreach($classMetric in $classMetrics){
        Add-Text $s $classMetric.T 0.98 $classMetric.Y 1.20 0.23 10 $C.White $true 1 'Aptos' 1 0 | Out-Null
        Add-Shape $s $msoShapeRoundedRectangle 2.25 ($classMetric.Y+0.01) 4.45 0.20 $C.Navy2 $C.Line | Out-Null
        Add-Shape $s $msoShapeRoundedRectangle 2.25 ($classMetric.Y+0.01) (4.45*$classMetric.V) 0.20 $classMetric.C $classMetric.C | Out-Null
        Add-Text $s $classMetric.S 6.86 ($classMetric.Y-0.01) 0.70 0.23 10 $classMetric.C $true 3 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 8.42 3.36 4.22 2.80 $C.Navy2 $C.Line | Out-Null
    Add-Text $s 'CẤU HÌNH & VAI TRÒ' 8.74 3.65 2.35 0.22 10 $C.Orange $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s '2.339 ảnh  ·  8.226 đối tượng' 8.74 4.08 3.30 0.28 15 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s '40 epoch · 640 px · pretrained · AMP' 8.74 4.49 3.32 0.24 10 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-Line $s 8.74 4.91 12.24 4.91 $C.Line 1 | Out-Null
    Add-Text $s '≈ 1,8 ms / ảnh' 8.74 5.14 1.75 0.30 16 $C.Teal $true 1 'Aptos Display' 1 0 | Out-Null
    Add-Text $s 'YOLO crop → Embed v4 → Qdrant' 8.74 5.55 3.18 0.23 10 $C.White $true 1 'Aptos' 1 0 | Out-Null
    Add-Text $s 'Không phát hiện / độ tin cậy thấp → dùng ảnh gốc.' 8.74 5.83 3.30 0.24 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    Add-AppendixFooter $s 'A5 / A6'

    # A6 — Evidence map
    $s = $deck.Slides.Add(38, $ppLayoutBlank)
    Add-Background $s
    Add-Title $s 'Phụ lục A6' 'Bản đồ bằng chứng & tài liệu bổ sung' 'Các đường dẫn nằm trong repository để truy vết hoặc mở khi hội đồng hỏi sâu.'
    $evidence=@(
        @{X=0.68;Y=1.98;T='Báo cáo kiểm thử';P='report-datn/Sections/07-KiemThuHeThong.tex';D='Thiết kế, gate, kết quả, traceability';C=$C.Blue},
        @{X=6.78;Y=1.98;T='Search evaluation';P='evals/search_evaluation/';D='Text · Image · Hybrid · baseline · ablation';C=$C.Teal},
        @{X=0.68;Y=3.20;T='Conversational AI';P='evals/conversational_ai_validation/';D='80 câu · critical gate · baseline A–D';C=$C.Orange},
        @{X=6.78;Y=3.20;T='Hiệu năng';P='report-datn/Evidence/performance/';D='Backend load · soak 2 giờ · AI concurrent';C=$C.Red},
        @{X=0.68;Y=4.42;T='E2E & khả dụng';P='report-datn/Evidence/e2e/ · availability/';D='Hybrid conversation · SMTP · correlation ID';C=$C.Blue},
        @{X=6.78;Y=4.42;T='Thiết kế & dữ liệu';P='report-datn/Images/ · DatabaseDiagrams/';D='Use case · architecture · ERD · sequence';C=$C.Teal}
    )
    foreach($e in $evidence){
        Add-Shape $s $msoShapeRoundedRectangle $e.X $e.Y 5.86 1.00 $C.Card $C.Line | Out-Null
        Add-Shape $s $msoShapeRectangle $e.X $e.Y 0.08 1.00 $e.C | Out-Null
        Add-Text $s $e.T ($e.X+0.28) ($e.Y+0.14) 1.84 0.28 13 $C.White $true 1 'Aptos Display' 1 0 | Out-Null
        Add-Text $s $e.P ($e.X+2.15) ($e.Y+0.14) 3.28 0.26 9 $e.C $true 1 'Consolas' 1 0 | Out-Null
        Add-Text $s $e.D ($e.X+0.28) ($e.Y+0.58) 5.12 0.25 9 $C.Muted $false 1 'Aptos' 1 0 | Out-Null
    }
    Add-Shape $s $msoShapeRoundedRectangle 0.68 5.90 11.96 0.64 $C.Teal $C.Teal | Out-Null
    Add-Text $s 'Toàn bộ số liệu trên slide chính đều có artifact hoặc bảng truy vết tương ứng trong repository.' 0.98 6.08 11.32 0.26 12 $C.Navy $true 2 'Aptos Display' 1 0 | Out-Null
    Add-AppendixFooter $s 'A6 / A6'

    # Metadata and output

    $deck.SaveAs($outputPath, $ppSaveAsOpenXMLPresentation)
    $deck.SaveAs($pdfPath, $ppSaveAsPDF)
    foreach ($slide in $deck.Slides) {
        $pngPath = Join-Path $previewDir ("slide-{0:D2}.png" -f $slide.SlideIndex)
        $slide.Export($pngPath, 'PNG', 1600, 900)
    }
}
finally {
    if ($deck) { $deck.Close() }
    if ($powerPoint) { $powerPoint.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($deck) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Write-Host "Created: $outputPath"
Write-Host "Created: $pdfPath"
Write-Host "Previews: $previewDir"
