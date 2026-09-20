param(
    [string]$InputPresentation,
    [string]$CoverPresentation = 'C:\Users\huynh\Downloads\Bản sao của XSTK.pptx',
    [string]$OutputPresentation
)

$ErrorActionPreference = 'Stop'

$invocationPath = $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($invocationPath)) {
    if ([string]::IsNullOrWhiteSpace($InputPresentation)) {
        throw 'InputPresentation is required when the script is invoked from an in-memory UTF-8 script block.'
    }
    $presentationDir = Split-Path -Parent ([System.IO.Path]::GetFullPath($InputPresentation))
    $scriptDir = Join-Path $presentationDir 'scripts'
} else {
    $scriptDir = Split-Path -Parent $invocationPath
    $presentationDir = Split-Path -Parent $scriptDir
}

if ([string]::IsNullOrWhiteSpace($InputPresentation)) {
    $InputPresentation = Join-Path $presentationDir 'DoAnTotNghiep.pptx'
}
if ([string]::IsNullOrWhiteSpace($OutputPresentation)) {
    $OutputPresentation = Join-Path $presentationDir 'DoAnTotNghiep.pptx'
}

$InputPresentation = [System.IO.Path]::GetFullPath($InputPresentation)
$CoverPresentation = [System.IO.Path]::GetFullPath($CoverPresentation)
$OutputPresentation = [System.IO.Path]::GetFullPath($OutputPresentation)
$outputPdf = [System.IO.Path]::ChangeExtension($OutputPresentation, '.pdf')

foreach ($required in @($InputPresentation, $CoverPresentation)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Không tìm thấy tệp: $required"
    }
}

if (-not $OutputPresentation.StartsWith($presentationDir, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Tệp đầu ra phải nằm trong thư mục presentation: $OutputPresentation"
}

function Rgb([int]$r, [int]$g, [int]$b) {
    return $r + ($g * 256) + ($b * 65536)
}

$old = @{
    Navy      = Rgb 8 22 40
    Navy2     = Rgb 13 35 58
    Ink       = Rgb 22 31 45
    White     = Rgb 247 250 252
    Muted     = Rgb 173 192 207
    Teal      = Rgb 39 207 185
    TealDark  = Rgb 13 129 125
    Blue      = Rgb 51 124 255
    Orange    = Rgb 255 151 74
    Red       = Rgb 245 93 105
    Card      = Rgb 20 45 70
    CardLight = Rgb 237 244 248
    Line      = Rgb 62 92 118
    DarkLine  = Rgb 29 55 79
    Gray      = Rgb 91 111 128
}

$new = @{
    Background = Rgb 255 255 255
    Ink        = Rgb 20 38 55
    Navy       = Rgb 20 55 88
    Muted      = Rgb 78 98 116
    Gray       = Rgb 103 120 135
    Teal       = Rgb 0 117 109
    TealDark   = Rgb 0 91 86
    Blue       = Rgb 31 91 160
    Orange     = Rgb 154 77 19
    Red        = Rgb 174 36 49
    Card       = Rgb 246 248 250
    CardAlt    = Rgb 238 244 248
    Line       = Rgb 202 214 224
    DarkLine   = Rgb 220 228 235
    PaleTeal   = Rgb 219 243 239
    PaleBlue   = Rgb 229 239 250
    PaleOrange = Rgb 252 236 221
    PaleRed    = Rgb 250 229 232
}

$fillMap = @{}
$fillMap[[string]$old.Navy] = $new.Background
$fillMap[[string]$old.Navy2] = $new.CardAlt
$fillMap[[string]$old.Ink] = $new.Ink
$fillMap[[string]$old.White] = $new.Background
$fillMap[[string]$old.Muted] = $new.CardAlt
$fillMap[[string]$old.Teal] = $new.PaleTeal
$fillMap[[string]$old.TealDark] = $new.PaleTeal
$fillMap[[string]$old.Blue] = $new.PaleBlue
$fillMap[[string]$old.Orange] = $new.PaleOrange
$fillMap[[string]$old.Red] = $new.PaleRed
$fillMap[[string]$old.Card] = $new.Card
$fillMap[[string]$old.CardLight] = $new.CardAlt
$fillMap[[string]$old.Line] = $new.Line
$fillMap[[string]$old.DarkLine] = $new.DarkLine
$fillMap[[string]$old.Gray] = $new.CardAlt

$fontMap = @{}
$fontMap[[string]$old.Navy] = $new.Navy
$fontMap[[string]$old.Navy2] = $new.Navy
$fontMap[[string]$old.Ink] = $new.Ink
$fontMap[[string]$old.White] = $new.Ink
$fontMap[[string]$old.Muted] = $new.Muted
$fontMap[[string]$old.Teal] = $new.Teal
$fontMap[[string]$old.TealDark] = $new.TealDark
$fontMap[[string]$old.Blue] = $new.Blue
$fontMap[[string]$old.Orange] = $new.Orange
$fontMap[[string]$old.Red] = $new.Red
$fontMap[[string]$old.Card] = $new.Navy
$fontMap[[string]$old.CardLight] = $new.Ink
$fontMap[[string]$old.Line] = $new.Muted
$fontMap[[string]$old.DarkLine] = $new.Gray
$fontMap[[string]$old.Gray] = $new.Gray

$lineMap = @{}
$lineMap[[string]$old.Navy] = $new.Navy
$lineMap[[string]$old.Navy2] = $new.Navy
$lineMap[[string]$old.Ink] = $new.Ink
$lineMap[[string]$old.White] = $new.Line
$lineMap[[string]$old.Muted] = $new.Line
$lineMap[[string]$old.Teal] = $new.Teal
$lineMap[[string]$old.TealDark] = $new.TealDark
$lineMap[[string]$old.Blue] = $new.Blue
$lineMap[[string]$old.Orange] = $new.Orange
$lineMap[[string]$old.Red] = $new.Red
$lineMap[[string]$old.Card] = $new.Line
$lineMap[[string]$old.CardLight] = $new.Line
$lineMap[[string]$old.Line] = $new.Line
$lineMap[[string]$old.DarkLine] = $new.DarkLine
$lineMap[[string]$old.Gray] = $new.Gray

function Set-MappedColor($colorObject, $map) {
    try {
        $key = [string]$colorObject.RGB
        if ($map.ContainsKey($key)) {
            $colorObject.RGB = $map[$key]
        }
    } catch {
        # Theme-controlled or unsupported color objects are left untouched.
    }
}

function Has-VisibleText($shape) {
    try {
        return ($shape.HasTextFrame -eq -1 -and $shape.TextFrame2.HasText -eq -1)
    } catch {
        return $false
    }
}

function Update-TextColors($shape) {
    if (-not (Has-VisibleText $shape)) {
        return
    }

    try {
        $runs = $shape.TextFrame2.TextRange.Runs()
        for ($runIndex = 1; $runIndex -le $runs.Count; $runIndex++) {
            Set-MappedColor $runs.Item($runIndex).Font.Fill.ForeColor $fontMap
        }
    } catch {
        Set-MappedColor $shape.TextFrame2.TextRange.Font.Fill.ForeColor $fontMap
    }
}

function Update-Shape($shape) {
    try {
        if ($shape.Type -eq 6) {
            for ($groupIndex = 1; $groupIndex -le $shape.GroupItems.Count; $groupIndex++) {
                Update-Shape $shape.GroupItems.Item($groupIndex)
            }
            return
        }
    } catch {
    }

    try {
        if ($shape.Fill.Visible -eq -1) {
            Set-MappedColor $shape.Fill.ForeColor $fillMap
        }
    } catch {
    }

    try {
        if ($shape.Line.Visible -eq -1) {
            Set-MappedColor $shape.Line.ForeColor $lineMap
        }
    } catch {
    }

    Update-TextColors $shape

    try {
        if ($shape.HasTable -eq -1) {
            for ($row = 1; $row -le $shape.Table.Rows.Count; $row++) {
                for ($column = 1; $column -le $shape.Table.Columns.Count; $column++) {
                    Update-Shape $shape.Table.Cell($row, $column).Shape
                }
            }
        }
    } catch {
    }

    try {
        if ($shape.Type -ne 13 -and $shape.Type -ne 11) {
            $shape.Shadow.Visible = 0
        }
    } catch {
    }
}

function Remove-DecorativeOvals($slide) {
    for ($shapeIndex = $slide.Shapes.Count; $shapeIndex -ge 1; $shapeIndex--) {
        $shape = $slide.Shapes.Item($shapeIndex)
        try {
            $isLargeOval = ($shape.Type -eq 1 -and $shape.AutoShapeType -eq 9 -and
                $shape.Width -ge 180 -and $shape.Height -ge 180)
            $isTranslucent = ($shape.Fill.Visible -eq -1 -and $shape.Fill.Transparency -ge 0.55)
            if ($isLargeOval -and $isTranslucent -and -not (Has-VisibleText $shape)) {
                $shape.Delete()
            }
        } catch {
        }
    }
}

function Add-TextBox {
    param(
        $slide,
        [string]$text,
        [double]$left,
        [double]$top,
        [double]$width,
        [double]$height,
        [double]$fontSize,
        [int]$fontColor,
        [bool]$bold = $false,
        [int]$alignment = 1,
        [string]$fontName = 'Aptos'
    )

    $box = $slide.Shapes.AddTextbox(1, $left, $top, $width, $height)
    $box.TextFrame2.MarginLeft = 3
    $box.TextFrame2.MarginRight = 3
    $box.TextFrame2.MarginTop = 2
    $box.TextFrame2.MarginBottom = 2
    $box.TextFrame2.WordWrap = -1
    $box.TextFrame2.AutoSize = 0
    $box.TextFrame.AutoSize = 0
    $box.TextFrame2.VerticalAnchor = 3
    $box.TextFrame2.TextRange.Text = $text
    $box.TextFrame2.TextRange.Font.Name = $fontName
    $box.TextFrame2.TextRange.Font.Size = $fontSize
    $box.TextFrame2.TextRange.Font.Bold = $(if ($bold) { -1 } else { 0 })
    $box.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $fontColor
    $box.TextFrame2.TextRange.ParagraphFormat.Alignment = $alignment
    # PowerPoint may collapse a newly populated textbox to one line even when
    # TextFrame2.AutoSize is disabled. Restore the requested box explicitly.
    $box.Left = $left
    $box.Top = $top
    $box.Width = $width
    $box.Height = $height
    return $box
}

function Replace-Cover($deck) {
    $inserted = $deck.Slides.InsertFromFile($CoverPresentation, 0, 1, 1)
    if ($inserted -ne 1) {
        throw 'Không thể chèn slide bìa từ tệp mẫu.'
    }

    # The former cover shifts to position 2 after inserting the source slide.
    $deck.Slides.Item(2).Delete()
    $cover = $deck.Slides.Item(1)

    for ($shapeIndex = $cover.Shapes.Count; $shapeIndex -ge 1; $shapeIndex--) {
        $shape = $cover.Shapes.Item($shapeIndex)
        $text = ''
        if (Has-VisibleText $shape) {
            $text = $shape.TextFrame2.TextRange.Text.Trim()
        }

        if ($shape.Name -eq 'Group 25' -or
            $text -eq 'BÁO CÁO' -or
            $text -eq 'BÀI TẬP LỚN' -or
            $text.StartsWith('GVHD: Huỳnh Thái Duy Phương')) {
            $shape.Delete()
            continue
        }

        if ($text -eq 'XÁC SUẤT THỐNG KÊ') {
            $shape.TextFrame2.TextRange.Text = 'ĐỒ ÁN TỐT NGHIỆP'
            $shape.TextFrame2.TextRange.Font.Name = 'Aptos Display'
            $shape.TextFrame2.TextRange.Font.Size = 18
            $shape.TextFrame2.TextRange.Font.Bold = -1
        } elseif ($text.StartsWith('ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH')) {
            $shape.TextFrame2.TextRange.Text = "ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH`rTRƯỜNG ĐẠI HỌC BÁCH KHOA`rKHOA KHOA HỌC VÀ KỸ THUẬT MÁY TÍNH"
            $shape.Top = 10
            $shape.Height = 64
            $shape.TextFrame2.TextRange.Font.Name = 'Aptos'
            $shape.TextFrame2.TextRange.Font.Size = 13.5
            $shape.TextFrame2.TextRange.Font.Bold = -1
            $shape.TextFrame2.TextRange.ParagraphFormat.Alignment = 2
        }
    }

    $white = Rgb 255 255 255
    $navy = Rgb 15 54 99
    $muted = Rgb 57 76 92

    Add-TextBox $cover "XÂY DỰNG TRỢ LÝ MUA SẮM`rĐA PHƯƠNG TIỆN SỬ DỤNG RAG`rVÀ COMPUTER VISION" 23 137 520 100 23 $white $true 1 'Aptos Display' | Out-Null
    Add-TextBox $cover 'Ngành:  Khoa học Máy tính' 103 231 370 17 10.5 $white $false 1 'Aptos' | Out-Null
    Add-TextBox $cover 'HỘI ĐỒNG:' 103 250 96 17 10 $white $true 1 'Aptos' | Out-Null
    $councilLine = $cover.Shapes.AddLine(205, 259, 470, 259)
    $councilLine.Line.ForeColor.RGB = $white
    $councilLine.Line.Weight = 1.1
    Add-TextBox $cover 'GVHD:  ThS. Võ Thanh Hùng' 103 269 350 17 10.5 $white $true 1 'Aptos' | Out-Null
    Add-TextBox $cover 'GVPB:' 103 288 60 17 10 $white $true 1 'Aptos' | Out-Null
    $reviewerLine = $cover.Shapes.AddLine(165, 297, 470, 297)
    $reviewerLine.Line.ForeColor.RGB = $white
    $reviewerLine.Line.Weight = 1.1

    $studentPanel = $cover.Shapes.AddShape(1, 77, 351, 350, 136)
    $studentPanel.Fill.ForeColor.RGB = $white
    $studentPanel.Line.ForeColor.RGB = $navy
    $studentPanel.Line.Weight = 1.25
    Add-TextBox $cover 'SINH VIÊN THỰC HIỆN' 96 365 310 22 11 $navy $true 1 'Aptos' | Out-Null
    Add-TextBox $cover 'Huỳnh Thái Minh Châu' 96 395 310 30 20 $navy $true 1 'Aptos Display' | Out-Null
    Add-TextBox $cover 'MSSV: 2210352' 96 430 155 22 12 $muted $true 1 'Aptos' | Out-Null
    Add-TextBox $cover 'TP. Hồ Chí Minh, tháng 9/2026' 96 457 290 18 10 $muted $false 1 'Aptos' | Out-Null
}

$archiveDir = Join-Path $presentationDir 'archive\versions'
$previewDir = Join-Path $presentationDir 'previews\white-theme'
New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
New-Item -ItemType Directory -Path $previewDir -Force | Out-Null

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupPresentation = Join-Path $archiveDir "DoAnTotNghiep-before-white-$stamp.pptx"
$backupPdf = Join-Path $archiveDir "DoAnTotNghiep-before-white-$stamp.pdf"
Copy-Item -LiteralPath $InputPresentation -Destination $backupPresentation
if (Test-Path -LiteralPath ([System.IO.Path]::ChangeExtension($InputPresentation, '.pdf'))) {
    Copy-Item -LiteralPath ([System.IO.Path]::ChangeExtension($InputPresentation, '.pdf')) -Destination $backupPdf
}

$tempPresentation = Join-Path $presentationDir "DoAnTotNghiep-white-$stamp.tmp.pptx"
$tempPdf = Join-Path $presentationDir "DoAnTotNghiep-white-$stamp.tmp.pdf"
$powerPoint = $null
$deck = $null

try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $powerPoint.Visible = -1
    $deck = $powerPoint.Presentations.Open($InputPresentation, 0, 0, 0)

    Replace-Cover $deck

    for ($slideIndex = 2; $slideIndex -le $deck.Slides.Count; $slideIndex++) {
        $slide = $deck.Slides.Item($slideIndex)
        $slide.FollowMasterBackground = 0
        $slide.Background.Fill.Solid()
        $slide.Background.Fill.ForeColor.RGB = $new.Background
        Remove-DecorativeOvals $slide
        for ($shapeIndex = 1; $shapeIndex -le $slide.Shapes.Count; $shapeIndex++) {
            Update-Shape $slide.Shapes.Item($shapeIndex)
        }
    }

    $deck.SaveAs($tempPresentation, 24)

    if (Test-Path -LiteralPath $tempPdf) {
        Remove-Item -LiteralPath $tempPdf -Force
    }
    $deck.SaveAs($tempPdf, 32)

    Get-ChildItem -LiteralPath $previewDir -Filter '*.png' -File | Remove-Item -Force
    for ($slideIndex = 1; $slideIndex -le $deck.Slides.Count; $slideIndex++) {
        $previewPath = Join-Path $previewDir ('slide-{0:D2}.png' -f $slideIndex)
        $deck.Slides.Item($slideIndex).Export($previewPath, 'PNG', 1600, 900)
    }
} finally {
    if ($deck) {
        $deck.Close()
    }
    if ($powerPoint) {
        $powerPoint.Quit()
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

if (-not (Test-Path -LiteralPath $tempPresentation -PathType Leaf)) {
    throw 'PowerPoint không tạo được tệp PPTX tạm.'
}
if (-not (Test-Path -LiteralPath $tempPdf -PathType Leaf)) {
    throw 'PowerPoint không tạo được tệp PDF tạm.'
}

Move-Item -LiteralPath $tempPresentation -Destination $OutputPresentation -Force
Move-Item -LiteralPath $tempPdf -Destination $outputPdf -Force

Write-Output "PPTX: $OutputPresentation"
Write-Output "PDF:  $outputPdf"
Write-Output "BACKUP PPTX: $backupPresentation"
if (Test-Path -LiteralPath $backupPdf) {
    Write-Output "BACKUP PDF:  $backupPdf"
}
Write-Output "PREVIEWS: $previewDir"
