# Ground-truth review — Conversational AI

> File chỉnh sửa chính: `ground_truth_review.csv`. Markdown này là bản đọc thuận tiện và
> sẽ được sinh lại từ CSV/source; không ghi quyết định review trực tiếp vào file này.

## Hướng dẫn quyết định

- `approved`: câu hỏi/reference/evidence đúng và đủ để làm acceptance ground truth.
- `needs_revision`: sửa nội dung tương ứng trong CSV rồi đổi thành `approved` khi hoàn tất.
- `rejected`: case mơ hồ, sai snapshot hoặc không nên nằm trong suite.
- `not_applicable`: chỉ dùng cho `evidence_status` khi `evidence_json=[]`.
- Điền `reviewer` cho mọi row đã đưa ra quyết định; `review_notes` ghi lý do sửa/reject.

## Tổng quan

- Testcase: **39**
- Structural validation: **PASS**
- Question status: `{"approved": 29, "pending": 10}`
- Reference status: `{"pending": 39}`
- Evidence status: `{"needs_revision": 17, "pending": 22}`
- Review warnings: `{}`

## Checklist review

Với từng case, kiểm tra:

1. Câu hỏi tự nhiên, không mơ hồ ngoài chủ đích và đúng category/difficulty.
2. Entity/source ID tồn tại và đúng sản phẩm trong snapshot.
3. Reference answer chỉ dùng dữ liệu nguồn và trả lời đúng trọng tâm.
4. `answer_must_include` không quá cứng với recommendation/follow-up.
5. Evidence `must_have` đủ để tạo câu trả lời; `nice_to_have` không bị dùng làm hard gate.
6. Case unanswerable không chứa policy tự bịa và hướng người dùng kiểm tra nguồn phù hợp.

## Nhóm `product_recommendation`

### `conv-rec-0016-t0`

- Session/turn: `conv-rec-0016` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `273`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Áo sơ mi màu Hồng / Trắng cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Áo sơ mi phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo sơ mi màu hồng và trắng caro đa kiểu có túi và dây buộc.

**Must include:** Áo sơ mi

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `22;27;29;40;64;67;68;89;93;101;103;105;128;133;137;158;162;164;169;171;181;187;190;194;195;200;215;220;227;228;229;230;239;243;247;248;249;255;256;260;263;264;266;273;276;297`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0016-t0-e1 | — | constraint | must_have | category=Áo sơ mi; color=Hồng / Trắng; gender=Nữ; valid_source_count=46 |
| conv-rec-0016-t0-e2 | 273 | supporting | nice_to_have | color=Hồng / Trắng |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 273 | Áo sơ mi màu hồng và trắng caro đa kiểu có túi và dây buộc | Áo sơ mi | Hồng / Trắng | 100% Cotton | Nữ |
| 22 | Áo sơ mi màu trắng poplin nẹp đính ngọc trai giả | Áo sơ mi | Trắng | 100% Cotton | Nữ |
| 27 | Áo sơ mi màu hồng poplin cotton cài cúc | Áo sơ mi | Hồng | 100% Cotton Yarn | Nữ |
| 29 | Áo sơ mi màu xanh dương và trắng không tay caro vai phồng | Áo sơ mi | Xanh dương / Trắng | 100% Cotton | Nữ |
| 40 | Áo sơ mi màu trắng crop ramie lyocell gấu rút dây | Áo sơ mi | Trắng | 58% Ramie, 42% Lyocell | Nữ |
| 64 | Áo sơ mi màu trắng ngà crop đai vai xếp ly trước | Áo sơ mi | Trắng ngà | 100% Polyester | Nữ |
| 67 | Áo sơ mi màu nâu và trắng ngà caro thêu hoa | Áo sơ mi | Nâu / Trắng ngà | 70% Cotton, 30% Polyester | Nữ |
| 68 | Áo sơ mi màu xanh navy và trắng caro thêu hoa | Áo sơ mi | Xanh navy / Trắng | 70% Cotton, 30% Polyester | Nữ |
| 89 | Áo sơ mi màu nâu và trắng ngà caro nhún chun | Áo sơ mi | Nâu / Trắng ngà | 81% Viscose, 19% Cotton | Nữ |
| 93 | Áo sơ mi màu trắng ngà và đỏ kẻ sọc nhún chun | Áo sơ mi | Trắng ngà / Đỏ | 83% Cotton, 17% Polyamide | Nữ |
| 101 | Áo sơ mi màu xanh dương và trắng không tay caro vai phồng | Áo sơ mi | Xanh dương / Trắng | 100% Polyester | Nữ |
| 103 | Áo sơ mi màu trắng ngà và đen kẻ sọc xếp ly phiên bản giới hạn | Áo sơ mi | Trắng ngà / Đen | 42% Cotton, 37% Viscose, 21% Polyamide | Nữ |
| 105 | Áo sơ mi màu trắng poplin ôm thắt nơ trước | Áo sơ mi | Trắng | 100% Cotton | Nữ |
| 128 | Áo sơ mi màu nâu và trắng ngà gingham dáng ngắn gấu bồng | Áo sơ mi | Nâu / Trắng ngà | 47% Polyester, 28% Cotton, 20% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 133 | Áo sơ mi màu trắng ngà oversize tay rộng | Áo sơ mi | Trắng ngà | 80% Viscose, 15% Polyester, 5% Polyamide | Nữ |
| 137 | Áo sơ mi màu hồng dáng ngắn kẻ sọc | Áo sơ mi | Hồng | 84% Cotton, 16% Polyamide | Nữ |
| 158 | Áo sơ mi màu trắng poplin safari | Áo sơ mi | Trắng | 56% Cotton, 44% Polyester | Nữ |
| 162 | Áo sơ mi màu hồng caro oversize | Áo sơ mi | Hồng | 99% Cotton, 1% Sợi co giãn (Elastane) | Nữ |
| 164 | Áo sơ mi màu trắng và xanh ngọc lam sọc chiết eo | Áo sơ mi | Trắng / Xanh ngọc lam | 75% Lyocell, 25% Polyamide | Nữ |
| 169 | Áo sơ mi màu trắng ngà satin có dây buộc | Áo sơ mi | Trắng ngà | 88% Lyocell, 12% Polyester | Nữ |
| 171 | Áo sơ mi màu xanh dương và trắng cotton pha form oversize kèm thắt lưng | Áo sơ mi | Xanh dương / Trắng | 73% Cotton, 27% Polyester | Nữ |
| 181 | Áo sơ mi màu trắng ngà satin gấu rút dây | Áo sơ mi | Trắng ngà | 100% Polyester | Nữ |
| 187 | Áo sơ mi màu trắng ngà poplin bèo đính đinh tán | Áo sơ mi | Trắng ngà | 100% Cotton | Nữ |
| 190 | Áo sơ mi màu trắng kem và nâu đậm kẻ sọc dọc dáng bomber | Áo sơ mi | Trắng kem | 100% Cotton | Nữ |
| 194 | Áo sơ mi màu trắng dáng rủ thêu gấu bất đối xứng | Áo sơ mi | Trắng | — | Nữ |
| 195 | Áo sơ mi màu trắng poplin tay phồng | Áo sơ mi | Trắng | 74% Cotton, 23% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 200 | Áo sơ mi màu xanh dương và trắng sọc cổ trụ có túi nắp | Áo sơ mi | Xanh dương / Trắng | 59% Polyester, 41% Viscose | Nữ |
| 215 | Áo sơ mi màu xanh dương và trắng sọc tay dài gấu bồng | Áo sơ mi | Xanh dương / Trắng | 95% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 220 | Áo sơ mi màu nâu và trắng poplin sọc có túi vuông | Áo sơ mi | Nâu / Trắng | 100% Cotton Yarn | Nữ |
| 227 | Áo sơ mi màu đen và trắng ngà họa tiết da thú viền lông vũ | Áo sơ mi | Đen / Trắng ngà | 100% Polyester | Nữ |
| 228 | Áo sơ mi màu trắng linen pha dáng rủ tay lỡ | Áo sơ mi | Trắng | 55% Vải lanh, 45% Viscose | Nữ |
| 229 | Áo sơ mi màu xanh dương và trắng linen pha sọc dáng rủ tay lỡ | Áo sơ mi | Xanh dương / Trắng | 55% Vải lanh, 45% Viscose | Nữ |
| 230 | Áo sơ mi màu hồng và trắng linen pha dáng rủ tay lỡ | Áo sơ mi | Hồng / Trắng | 55% Vải lanh, 45% Viscose | Nữ |
| 239 | Áo sơ mi màu trắng poplin gấu tròn bất đối xứng | Áo sơ mi | Trắng | 100% Cotton | Nữ |
| 243 | Áo sơ mi màu be và hồng viscose dáng rủ cổ thắt nơ | Áo sơ mi | Be / Hồng | 100% Viscose | Nữ |
| 247 | Áo sơ mi màu hồng và trắng poplin sọc tay bồng | Áo sơ mi | Hồng / Trắng | 86% Viscose, 14% Polyamide | Nữ |
| 248 | Áo sơ mi màu trắng poplin sọc tay bồng | Áo sơ mi | Trắng | 83% Cotton, 17% Polyamide | Nữ |
| 249 | Áo sơ mi màu trắng poplin sọc tay bồng | Áo sơ mi | Trắng | 86% Viscose, 14% Polyamide | Nữ |
| 255 | Áo sơ mi màu trắng ngà dáng cape sợi kim tuyến | Áo sơ mi | Trắng ngà | 59% Cotton, 39% Viscose, 1% Polyamide, 1% Polyamide Metallised Fibre | Nữ |
| 256 | Áo sơ mi màu trắng linen pha oversize phối ren | Áo sơ mi | Trắng | 55% Vải lanh, 45% Viscose | Nữ |
| 260 | Áo sơ mi màu trắng ngà thêu viền lông vũ | Áo sơ mi | Trắng ngà | 54% Cotton, 46% Polyester | Nữ |
| 263 | Áo sơ mi màu trắng ngà và đen tay ngắn thắt nơ ở gấu | Áo sơ mi | Trắng ngà / Đen | 82% Viscose, 18% Polyamide | Nữ |
| 264 | Áo sơ mi màu trắng tay bồng phối ren | Áo sơ mi | Trắng | 53% Viscose, 32% Polyamide, 14% Polyester, 1% Sợi co giãn (Elastane) | Nữ |
| 266 | Áo sơ mi màu xanh dương và trắng sọc sợi kim tuyến xếp ly phối ren | Áo sơ mi | Xanh dương / Trắng | 67% Cotton, 31% Vải lanh, 2% Polyester Metallised Fibre | Nữ |
| 276 | Áo sơ mi màu trắng ngà poplin gấu bồng | Áo sơ mi | Trắng ngà | 100% Cotton | Nữ |
| 297 | Áo sơ mi màu nâu và trắng sọc oversize tay dơi | Áo sơ mi | Nâu / Trắng | 100% Cotton Yarn | Nữ |

### `conv-rec-0013-t0`

- Session/turn: `conv-rec-0013` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `1270`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Áo kiểu màu Trắng cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Áo kiểu phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo kiểu màu trắng cao cấp họa tiết jacquard hoa bất đối xứng.

**Must include:** Áo kiểu

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `26;49;81;98;123;185;199;202;209;242;244;283;1025;1051;1106;1154;1169;1175;1179;1194;1208;1247;1268;1270;1329;1331;1343;1348;1426;1428;1436;1465;1486;1523;1552;1570;1578;1584;1604;1617;1641;1659;1661;1700`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0013-t0-e1 | — | constraint | must_have | category=Áo kiểu; color=Trắng; gender=Nữ; valid_source_count=44 |
| conv-rec-0013-t0-e2 | 1270 | supporting | nice_to_have | color=Trắng |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1270 | Áo kiểu màu trắng cao cấp họa tiết jacquard hoa bất đối xứng | Áo kiểu | Trắng | 50% Viscose, 50% Lyocell | Nữ |
| 26 | Áo kiểu màu trắng poplin có bèo | Áo kiểu | Trắng | 100% Cotton | Nữ |
| 49 | Áo kiểu màu trắng kẻ sọc cổ Johnny tay dài vạt bất đối xứng | Áo kiểu | Trắng | 71% Viscose, 24% Vải lanh, 5% Lyocell | Nữ |
| 81 | Áo kiểu màu trắng ngà dài tay xếp ly bèo nhún | Áo kiểu | Trắng ngà | 100% Polyester | Nữ |
| 98 | Áo kiểu màu trắng bèo nơ | Áo kiểu | Trắng | 82% Viscose, 18% Polyamide | Nữ |
| 123 | Áo kiểu màu nâu và trắng kẻ sọc nơ cổ v | Áo kiểu | Nâu / Trắng | 100% Cotton | Nữ |
| 185 | Áo kiểu màu trắng ngà satin bèo vai nổi | Áo kiểu | Trắng ngà | 100% Polyester | Nữ |
| 199 | Áo kiểu màu trắng ngà và đen bồng bèo thêu trắng đen | Áo kiểu | Trắng ngà / Đen | 87% Lyocell, 13% Polyamide | Nữ |
| 202 | Áo kiểu màu trắng ngà satin cổ cao | Áo kiểu | Trắng ngà | 100% Polyester | Nữ |
| 209 | Áo kiểu màu trắng ren bèo nhún không tay | Áo kiểu | Trắng | 71% Cotton, 29% Polyester | Nữ |
| 242 | Áo kiểu màu trắng ngà xếp ly nơ cổ tròn | Áo kiểu | Trắng ngà | 100% Viscose | Nữ |
| 244 | Áo kiểu màu trắng chấm bi buộc dây xếp bèo | Áo kiểu | Trắng | 100% Viscose | Nữ |
| 283 | Áo kiểu màu trắng bèo nhún dập ly | Áo kiểu | Trắng | 74% Viscose, 26% Polyamide | Nữ |
| 1025 | Áo kiểu màu trắng ngà và đỏ viscose in họa tiết | Áo kiểu | Trắng ngà / Đỏ | 100% Viscose | Nữ |
| 1051 | Áo kiểu màu trắng ngà bất đối xứng cotton | Áo kiểu | Trắng ngà | 56% Cotton, 38% Viscose, 6% Sợi co giãn (Elastane) | Nữ |
| 1106 | Áo kiểu màu đen và trắng vải voan họa tiết tay bồng | Áo kiểu | Đen / Trắng | 100% Viscose | Nữ |
| 1154 | Áo kiểu màu trắng ngà cổ cao sát nách | Áo kiểu | Trắng ngà | 77% Polyester, 20% Viscose, 3% Sợi co giãn (Elastane) | Nữ |
| 1169 | Áo kiểu màu trắng ngà smocked tay dài cổ V đính nơ | Áo kiểu | Trắng ngà | 59% Cotton, 40% Polyester, 1% Sợi co giãn (Elastane) | Nữ |
| 1175 | Áo kiểu màu trắng ngà dáng corset trễ vai vải dập nổi cổ ngang | Áo kiểu | Trắng ngà | 80% Polyester, 17% Polyamide, 3% Sợi co giãn (Elastane) | Nữ |
| 1179 | Áo kiểu màu trắng ngà và vàng poplin họa tiết hoa | Áo kiểu | Trắng ngà / Vàng | 96% Cotton, 4% Sợi co giãn (Elastane) | Nữ |
| 1194 | Áo kiểu màu trắng dáng crop tay phồng vải poplin | Áo kiểu | Trắng | 100% Cotton | Nữ |
| 1208 | Áo kiểu màu trắng và xanh navy cổ v dây chéo vải dệt | Áo kiểu | Trắng / Xanh navy | 61% Polyester, 20% Cotton, 17% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1247 | Áo kiểu màu trắng ngà tay bồng | Áo kiểu | Trắng ngà | 100% Polyester | Nữ |
| 1268 | Áo kiểu màu trắng dáng quây đính đinh tán | Áo kiểu | Trắng | 56% Polyamide, 38% Cotton, 6% Sợi co giãn (Elastane) | Nữ |
| 1329 | Áo kiểu màu trắng tay phồng thắt nơ phía trước | Áo kiểu | Trắng | 48% Cotton, 47% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 1331 | Áo kiểu màu trắng ngà không tay viền tua rua | Áo kiểu | Trắng ngà | 9% Vải lanh | Nữ |
| 1343 | Áo kiểu màu trắng ngà hở lưng tay ngắn | Áo kiểu | Trắng ngà | 74% Viscose, 26% Acetate | Nữ |
| 1348 | Áo kiểu màu đen và trắng ngà sọc vải tweed trễ vai | Áo kiểu | Đen / Trắng ngà | 75% Polyester, 22% Viscose, 3% Sợi co giãn (Elastane) | Nữ |
| 1426 | Áo kiểu màu đen và trắng ngà tay phồng cổ vuông phối vải bouclé | Áo kiểu | Đen / Trắng ngà | — | Nữ |
| 1428 | Áo kiểu màu trắng ngà trễ vai tay dài đính khóa kim loại | Áo kiểu | Trắng ngà | 54% Polyester, 45% Viscose, 1% Sợi co giãn (Elastane) | Nữ |
| 1436 | Áo kiểu màu trắng ngà cổ vest dài tay khóa kéo | Áo kiểu | Trắng ngà | 45% Acrylic, 37% Polyester, 12% Polyamide, 5% Len lông cừu, 1% Sợi co giãn (Elastane) | Nữ |
| 1465 | Áo kiểu màu trắng vải lanh pha cổ vest chiết ly | Áo kiểu | Trắng | 70% Viscose, 30% Vải lanh | Nữ |
| 1486 | Áo kiểu màu trắng ngà cổ v tay bồng khóa kéo | Áo kiểu | Trắng ngà | 100% Polyester | Nữ |
| 1523 | Áo kiểu màu trắng ngà tay phồng cổ tròn | Áo kiểu | Trắng ngà | 55% Cotton, 42% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 1552 | Áo kiểu màu trắng và xanh da trời sọc nơ cổ v | Áo kiểu | Trắng / Xanh da trời | 100% Cotton | Nữ |
| 1570 | Áo kiểu màu trắng tay ngắn cut-out đính nơ | Áo kiểu | Trắng | 100% Cotton | Nữ |
| 1578 | Áo kiểu màu đen và trắng dáng quây đính sequin chấm bi | Áo kiểu | Đen / Trắng | 100% Polyester | Nữ |
| 1584 | Áo kiểu màu trắng ngà xuyên thấu viền bèo | Áo kiểu | Trắng ngà | 68% Viscose, 32% Polyester | Nữ |
| 1604 | Áo kiểu màu trắng dáng quây corset trễ vai | Áo kiểu | Trắng | 92% Polyester, 8% Sợi co giãn (Elastane) | Nữ |
| 1617 | Áo kiểu màu trắng ngà satin bất đối xứng tay dài | Áo kiểu | Trắng ngà | 100% Viscose | Nữ |
| 1641 | Áo kiểu màu trắng ngà và xanh dương hai dây caro smocked | Áo kiểu | Trắng ngà / Xanh dương | 72% Polyester, 27% Cotton, 1% Sợi co giãn (Elastane) | Nữ |
| 1659 | Áo kiểu màu trắng cổ v tay bồng xếp ly | Áo kiểu | Trắng | 95% Cotton, 5% Sợi co giãn (Elastane) | Nữ |
| 1661 | Áo kiểu màu trắng ngà basic tay ngắn vải rustic cổ tròn | Áo kiểu | Trắng ngà | 98% Polyester, 2% Sợi co giãn (Elastane) | Nữ |
| 1700 | Áo kiểu màu trắng tay bồng nơ | Áo kiểu | Trắng | 100% Cotton | Nữ |

### `conv-rec-0005-t0`

- Session/turn: `conv-rec-0005` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `337`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Váy & Đầm màu Đỏ rượu vang cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Váy & Đầm phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Đầm mini màu đỏ rượu vang vải interlock mềm cổ tròn.

**Must include:** Váy & Đầm

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `337;363;502;536;547;638;652;653;691`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0005-t0-e1 | — | constraint | must_have | category=Váy & Đầm; color=Đỏ rượu vang; gender=Nữ; valid_source_count=9 |
| conv-rec-0005-t0-e2 | 337 | supporting | nice_to_have | color=Đỏ rượu vang |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 337 | Đầm mini màu đỏ rượu vang vải interlock mềm cổ tròn | Váy & Đầm | Đỏ rượu vang | 75% Cotton, 17% Polyester, 8% Sợi co giãn (Elastane) | Nữ |
| 363 | Đầm mini màu trắng ngà và vàng kẻ sọc cổ V | Váy & Đầm | Trắng ngà / Vàng | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 502 | Đầm mini hai dây màu vàng đậm cổ tim co giãn | Váy & Đầm | Vàng đậm | 60% Polyamide, 40% Sợi co giãn (Elastane) | Nữ |
| 536 | Đầm màu vàng bơ lyocell linen eo ôm xếp ly | Váy & Đầm | Vàng bơ | 25% Linen Blend Yarn | Nữ |
| 547 | Đầm midi hai dây màu vàng caro lưng nhún chun | Váy & Đầm | Vàng | 63% Polyester, 36% Viscose, 1% Sợi co giãn (Elastane) | Nữ |
| 638 | Đầm midi màu vàng họa tiết viền bèo gấu bất đối xứng | Váy & Đầm | Vàng | 100% Polyester | Nữ |
| 652 | Đầm maxi suông màu vàng chanh georgette hở lưng | Váy & Đầm | Vàng chanh | 100% Viscose | Nữ |
| 653 | Đầm mini màu vàng pastel tay xếp ly túi giả | Váy & Đầm | Vàng pastel | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 691 | Đầm mini màu nâu vàng nhạt kẻ sọc cổ V | Váy & Đầm | Nâu vàng nhạt | 63% Polyester, 32% Viscose, 5% Sợi co giãn (Elastane) | Nữ |

### `conv-rec-0019-t0`

- Session/turn: `conv-rec-0019` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `745`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Áo thun màu Nâu đậm cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Áo thun phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo thun màu nâu đậm tay ngắn xẻ sau.

**Must include:** Áo thun

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `703;718;745;749;756;762;764;768;769;774;782;803;804;806;857;895;896;907;925;932;950;953;959;963;972;1011;1015`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0019-t0-e1 | — | constraint | must_have | category=Áo thun; color=Nâu đậm; gender=Nữ; valid_source_count=27 |
| conv-rec-0019-t0-e2 | 745 | supporting | nice_to_have | color=Nâu đậm |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 745 | Áo thun màu nâu đậm tay ngắn xẻ sau | Áo thun | Nâu đậm | 96% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 703 | Áo thun màu nâu dáng ôm tay dài | Áo thun | Nâu | 48% Cotton, 47% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 718 | Áo thun màu nâu thuốc lá tay dài gấu rút dây | Áo thun | Nâu thuốc lá | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 749 | Áo thun màu nâu chocolate viền tương phản | Áo thun | Nâu chocolate | 70% Modal, 30% Polyester | Nữ |
| 756 | Áo thun màu nâu cổ cao bất đối xứng | Áo thun | Nâu | 19% Wool Yarn | Nữ |
| 762 | Áo thun màu nâu chocolate gân | Áo thun | Nâu chocolate | 96% Cotton, 4% Sợi co giãn (Elastane) | Nữ |
| 764 | Áo thun màu nâu nhạt tối giản tay ngắn | Áo thun | Nâu nhạt | 100% Cotton | Nữ |
| 768 | Áo thun màu nâu viền tương phản | Áo thun | Nâu | 95% Cotton, 5% Sợi co giãn (Elastane) | Nữ |
| 769 | Áo thun màu nâu chocolate hiệu ứng kép tay ngắn | Áo thun | Nâu chocolate | 100% Cotton | Nữ |
| 774 | Áo thun màu nâu chocolate tay dài vải interlock co giãn | Áo thun | Nâu chocolate | — | Nữ |
| 782 | Áo thun màu nâu chocolate crop tay bồng ngắn | Áo thun | Nâu chocolate | 100% Cotton | Nữ |
| 803 | Áo thun màu nâu tay dài in chữ wash | Áo thun | Nâu | 100% Cotton Yarn | Nữ |
| 804 | Áo thun màu nâu và nâu xám cổ v tay dài buộc eo | Áo thun | Nâu / Nâu xám | 100% Cotton | Nữ |
| 806 | Áo thun màu nâu melange raglan tay ngắn | Áo thun | Nâu melange | 91% Acrylic, 9% Sợi co giãn (Elastane) | Nữ |
| 857 | Áo thun màu nâu và xanh lá lyocell hemp sọc tay ngắn | Áo thun | Nâu / Xanh lá | 87% Lyocell, 13% Gai dầu | Nữ |
| 895 | Áo thun màu nâu sát nách bất đối xứng | Áo thun | Nâu | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |
| 896 | Áo thun màu be và nâu tay ngắn phối vải tương phản | Áo thun | Be / Nâu | 89% Acrylic, 11% Sợi co giãn (Elastane) | Nữ |
| 907 | Áo thun màu nâu đậm dài tay cổ tròn | Áo thun | Nâu đậm | 60% Cotton, 40% Polyester | Nữ |
| 925 | Áo thun màu nâu in hình disney the muppets | Áo thun | Nâu | 50% Cotton, 50% Modal | Nữ |
| 932 | Áo thun màu nâu camel in slogan | Áo thun | Nâu camel | 48% Cotton, 48% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 950 | Áo thun màu nâu sọc thêu tay dài | Áo thun | Nâu sọc | 100% Cotton Yarn | Nữ |
| 953 | Áo thun màu nâu chocolate phối ren | Áo thun | Nâu chocolate | Cotton | Nữ |
| 959 | Áo thun màu nâu chocolate phối voan | Áo thun | Nâu chocolate | 95% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 963 | Áo thun màu nâu và xanh dương raglan phối màu nâu | Áo thun | Nâu / Xanh dương | 96% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 972 | Áo thun màu cát và nâu ba lỗ phong cách rustic | Áo thun | Màu cát / Nâu | 100% Cotton | Nữ |
| 1011 | Áo thun màu nâu melange basic tay ngắn | Áo thun | Nâu melange | 57% Cotton, 38% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 1015 | Áo thun màu nâu chocolate tay ngắn in hình elvis | Áo thun | Nâu chocolate | 100% Cotton | Nữ |

### `conv-rec-0010-t0`

- Session/turn: `conv-rec-0010` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `1674`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Áo hai dây, áo sát nách & áo yếm màu Vàng ánh kim cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Áo hai dây, áo sát nách & áo yếm phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo hai dây màu vàng ánh kim cổ v đính sequin thêu.

**Must include:** Áo hai dây, áo sát nách & áo yếm

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `1140;1183;1200;1230;1286;1292;1453;1574;1611;1674`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0010-t0-e1 | — | constraint | must_have | category=Áo hai dây, áo sát nách & áo yếm; color=Vàng ánh kim; gender=Nữ; valid_source_count=10 |
| conv-rec-0010-t0-e2 | 1674 | supporting | nice_to_have | color=Vàng ánh kim |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1674 | Áo hai dây màu vàng ánh kim cổ v đính sequin thêu | Áo hai dây, áo sát nách & áo yếm | Vàng ánh kim | 100% Polyester | Nữ |
| 1140 | Áo hai dây màu vàng pastel ren xếp ly | Áo hai dây, áo sát nách & áo yếm | Vàng pastel | 98% Polyamide, 2% Sợi co giãn (Elastane) | Nữ |
| 1183 | Áo yếm màu vàng dệt kim dáng rộng | Áo hai dây, áo sát nách & áo yếm | Vàng | 76% Cotton, 24% Elastomultiester | Nữ |
| 1200 | Áo yếm màu vàng cổ yếm đính chuỗi hạt | Áo hai dây, áo sát nách & áo yếm | Vàng | 100% Polyester | Nữ |
| 1230 | Áo yếm màu vàng nhạt lưng hở xếp ly | Áo hai dây, áo sát nách & áo yếm | Vàng nhạt | 61% Cotton, 38% Polyester, 1% Sợi co giãn (Elastane) | Nữ |
| 1286 | Áo hai dây màu vàng pastel corset hoa thêu co giãn | Áo hai dây, áo sát nách & áo yếm | Vàng pastel | 97% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 1292 | Áo yếm màu vàng chanh georgette cổ bèo | Áo hai dây, áo sát nách & áo yếm | Vàng chanh | 100% Viscose | Nữ |
| 1453 | Áo yếm màu vàng nhạt vàng vải lưới chấm bi | Áo hai dây, áo sát nách & áo yếm | Vàng nhạt | 95% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 1574 | Áo hai dây màu vàng kim sa lệch vai | Áo hai dây, áo sát nách & áo yếm | Vàng | 45% Polyester, 27% Polyamide, 27% Viscose, 1% Sợi co giãn (Elastane) | Nữ |
| 1611 | Áo hai dây màu vàng caro viền ren | Áo hai dây, áo sát nách & áo yếm | Vàng | 63% Polyester, 36% Viscose, 1% Sợi co giãn (Elastane) | Nữ |

### `conv-rec-0003-t0`

- Session/turn: `conv-rec-0003` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `2004`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Quần dài màu Nâu sọc cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Quần dài phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Quần dài màu nâu sọc mảnh có quai đai.

**Must include:** Quần dài

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `1746;1749;1765;1767;1782;1784;1821;1830;1841;1846;1850;1901;1902;1909;1912;1922;1926;1937;1942;1943;1954;1964;1965;1974;1976;1982;1988;1990;2004;2006;2009;2010;2014;2015;2016;2024;2026;2031;2032`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0003-t0-e1 | — | constraint | must_have | category=Quần dài; color=Nâu sọc; gender=Nữ; valid_source_count=39 |
| conv-rec-0003-t0-e2 | 2004 | supporting | nice_to_have | color=Nâu sọc |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 2004 | Quần dài màu nâu sọc mảnh có quai đai | Quần dài | Nâu sọc | 67% Polyester, 29% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 1746 | Quần dài ống rộng màu nâu chồn vải interlock hiệu ứng wash | Quần dài | Nâu chồn | 80% Cotton, 20% Polyester | Nữ |
| 1749 | Quần dài màu xám và nâu vàng dáng phồng họa tiết caro | Quần dài | Xám / Nâu vàng | 63% Polyester, 32% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 1765 | Quần sarouel màu xám nâu cạp thun dây rút | Quần dài | Xám nâu | 63% Lyocell, 31% Viscose, 6% Polyamide | Nữ |
| 1767 | Quần dài ống loe màu nâu và trắng ngà cạp thấp sọc mảnh | Quần dài | Nâu / Trắng ngà | 93% Polyester, 5% Sợi co giãn (Elastane), 2% Viscose | Nữ |
| 1782 | Quần dài ống suông màu nâu vân xương cá kèm thắt lưng | Quần dài | Nâu | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1784 | Quần Culotte màu nâu và trắng ngà caro thêu | Quần dài | Nâu / Trắng ngà | 70% Cotton, 30% Polyester | Nữ |
| 1821 | Quần dài lửng màu nâu đậm ly chiết phía trước kèm thắt lưng | Quần dài | Nâu đậm | 74% Polyester, 20% Viscose, 6% Sợi co giãn (Elastane) | Nữ |
| 1830 | Quần dài ống suông màu nâu chocolate vân nổi cạp dây rút | Quần dài | Nâu chocolate | 99% Polyester, 1% Sợi co giãn (Elastane) | Nữ |
| 1841 | Quần dài ống loe màu nâu melange seamless cạp thun | Quần dài | Nâu melange | 48% Polyamide, 47% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 1846 | Quần dài ống loe màu nâu đậm vải linen pha xẻ gấu | Quần dài | Nâu đậm | 68% Viscose, 30% Vải lanh, 2% Sợi co giãn (Elastane) | Nữ |
| 1850 | Quần sarouel màu nâu nhạt cạp thun dây rút | Quần dài | Nâu nhạt | 75% Viscose, 25% Polyamide | Nữ |
| 1901 | Quần dài ống rộng màu nâu vải thô kẻ sọc | Quần dài | Nâu | 70% Polyester, 27% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1902 | Quần dài ống suông màu nâu đậm vải piqué thắt lưng tương phản | Quần dài | Nâu đậm | 98% Polyester, 2% Sợi co giãn (Elastane) | Nữ |
| 1909 | Quần palazzo màu nâu vân nổi cạp dây rút | Quần dài | Nâu | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |
| 1912 | Quần dài ống loe màu nâu vải interlock mềm cạp thun | Quần dài | Nâu | 75% Cotton, 17% Polyester, 8% Sợi co giãn (Elastane) | Nữ |
| 1922 | Quần dài màu nâu chocolate da lộn giả cạp cao | Quần dài | Nâu chocolate | 93% Polyester, 7% Sợi co giãn (Elastane) | Nữ |
| 1926 | Quần dài ống loe màu nâu camel túi vá | Quần dài | Nâu camel | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1937 | Quần dài ống loe màu nâu cạp cao túi khóa kéo | Quần dài | Nâu | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1942 | Quần cargo ống suông màu nâu hiệu ứng phai màu | Quần dài | Nâu | 100% Cotton | Nữ |
| 1943 | Quần dài lửng màu nâu melange cạp cao đường may nổi | Quần dài | Nâu melange | 63% Polyester, 31% Viscose, 6% Sợi co giãn (Elastane) | Nữ |
| 1954 | Quần dài màu nâu và nâu xám vải nhăn bo gấu | Quần dài | Nâu / Nâu xám | 77% Polyester, 23% Polyamide | Nữ |
| 1964 | Quần dài ống suông màu nâu melange cạp cao | Quần dài | Nâu melange | 49% Polyester, 31% Viscose, 15% Polyamide, 5% Sợi co giãn (Elastane) | Nữ |
| 1965 | Quần dài ống suông màu nâu đậm hàng cúc kim loại | Quần dài | Nâu đậm | 56% Cotton, 41% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 1974 | Quần jogger màu nâu đậm cạp dây rút bo gấu | Quần dài | Nâu đậm | 68% Viscose, 32% Vải lanh | Nữ |
| 1976 | Quần dài lửng ống loe màu nâu camel pha len đường ly ép | Quần dài | Nâu camel | 45% Len lông cừu, 40% Polyester, 15% Vải lanh | Nữ |
| 1982 | Quần dài màu nâu và xanh dương họa tiết caro ly trước | Quần dài | Nâu / Xanh dương | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1988 | Quần dài màu nâu vàng nhạt cạp quấn túi nắp cài cúc | Quần dài | Nâu vàng nhạt | 54% Cotton, 39% Polyamide, 7% Sợi co giãn (Elastane) | Nữ |
| 1990 | Quần dài màu nâu chồn pha len ly trước | Quần dài | Nâu chồn | 50% Wool Blend | Nữ |
| 2006 | Quần dài màu nâu đậm pha len ly trước | Quần dài | Nâu đậm | 15% Len lông cừu | Nữ |
| 2009 | Quần dài ống rộng màu nâu melange ly chiết phía trước | Quần dài | Nâu melange | 66% Polyester, 29% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 2010 | Quần dài màu nâu nhạt vải rủ gấu nhún điều chỉnh | Quần dài | Nâu nhạt | 60% Lyocell, 23% Gai dầu, 17% Cotton | Nữ |
| 2014 | Quần dài ống suông màu nâu chồn lưng vừa | Quần dài | Nâu chồn | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 2015 | Quần baggy màu nâu nhạt cạp thấp chi tiết bất đối xứng | Quần dài | Nâu nhạt | 96% Polyester, 4% Sợi co giãn (Elastane) | Nữ |
| 2016 | Quần Capri màu nâu vàng nhạt sọc mảnh | Quần dài | Nâu vàng nhạt | 63% Polyester, 32% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 2024 | Quần dài lửng ống loe màu nâu cạp thấp | Quần dài | Nâu | 71% Cotton, 24% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 2026 | Quần dài ống loe màu nâu đường may nổi hai bên | Quần dài | Nâu | 71% Polyester, 22% Viscose, 7% Sợi co giãn (Elastane) | Nữ |
| 2031 | Quần dài ống suông màu nâu vải nỉ cạp dây rút | Quần dài | Nâu | Cotton pha | Nữ |
| 2032 | Quần dài ống suông màu nâu cạp cao kèm thắt lưng gấu lật | Quần dài | Nâu | 75% Polyester, 19% Viscose, 6% Sợi co giãn (Elastane) | Nữ |

### `conv-rec-0008-t0`

- Session/turn: `conv-rec-0008` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `307`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Váy & Đầm màu Hồng pastel cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Váy & Đầm phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Đầm màu hồng pastel ren bèo nhún gấu bất đối xứng.

**Must include:** Váy & Đầm

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `307;332;384;388;413;451;508;552;579;646;655;664;671`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0008-t0-e1 | — | constraint | must_have | category=Váy & Đầm; color=Hồng pastel; gender=Nữ; valid_source_count=13 |
| conv-rec-0008-t0-e2 | 307 | supporting | nice_to_have | color=Hồng pastel |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 307 | Đầm màu hồng pastel ren bèo nhún gấu bất đối xứng | Váy & Đầm | Hồng pastel | 91% Polyester, 9% Sợi co giãn (Elastane) | Nữ |
| 332 | Đầm mini màu trắng và hồng vân nổi cổ cao | Váy & Đầm | Trắng / Hồng | 50% Polyester, 47% Cotton, 3% Viscose | Nữ |
| 384 | Đầm midi màu hồng fuchsia đậm xếp ly cổ V | Váy & Đầm | Hồng fuchsia đậm | 100% Polyester | Nữ |
| 388 | Đầm mini màu hồng nhạt dáng phồng vải poplin cổ yếm | Váy & Đầm | Hồng nhạt | 57% Cotton, 43% Viscose | Nữ |
| 413 | Đầm midi suông màu hồng cá hồi nhạt vải nhăn hở lưng | Váy & Đầm | Hồng cá hồi nhạt | 48% Cotton, 44% Polyester, 8% Sợi ánh kim | Nữ |
| 451 | Đầm midi màu hồng thân nhún chun tay phồng | Váy & Đầm | Hồng | 64% Cotton, 35% Viscose, 1% Sợi co giãn (Elastane) | Nữ |
| 508 | Đầm midi suông màu be và hồng phối vải đồng tông xếp ly | Váy & Đầm | Be / Hồng | 87% Polyamide, 13% Sợi co giãn (Elastane) | Nữ |
| 552 | Đầm mini màu hồng kẻ sọc phối ren tương phản nhún | Váy & Đầm | Hồng | 100% Viscose | Nữ |
| 579 | Đầm mini màu hồng nhạt phối vải viền bèo gấu bất đối xứng | Váy & Đầm | Hồng nhạt | 100% Polyester | Nữ |
| 646 | Đầm mini màu hồng phấn phối ren tương phản hở lưng | Váy & Đầm | Hồng phấn | 100% Viscose | Nữ |
| 655 | Đầm mini màu hồng và tím khói họa tiết hoa hở lưng gấu bèo | Váy & Đầm | Hồng / Tím khói | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 664 | Đầm mini cổ yếm màu hồng xếp nếp vòng nút | Váy & Đầm | Hồng | 96% Polyester, 4% Sợi co giãn (Elastane) | Nữ |
| 671 | Đầm midi màu be và hồng xếp ly hai bên viền bèo | Váy & Đầm | Be / Hồng | 100% Polyester | Nữ |

### `conv-rec-0018-t0`

- Session/turn: `conv-rec-0018` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `718`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Áo thun màu Nâu thuốc lá cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Áo thun phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo thun màu nâu thuốc lá tay dài gấu rút dây.

**Must include:** Áo thun

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `703;718;745;749;756;762;764;768;769;774;782;803;804;806;857;895;896;907;925;932;950;953;959;963;972;1011;1015`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0018-t0-e1 | — | constraint | must_have | category=Áo thun; color=Nâu thuốc lá; gender=Nữ; valid_source_count=27 |
| conv-rec-0018-t0-e2 | 718 | supporting | nice_to_have | color=Nâu thuốc lá |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 718 | Áo thun màu nâu thuốc lá tay dài gấu rút dây | Áo thun | Nâu thuốc lá | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 703 | Áo thun màu nâu dáng ôm tay dài | Áo thun | Nâu | 48% Cotton, 47% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 745 | Áo thun màu nâu đậm tay ngắn xẻ sau | Áo thun | Nâu đậm | 96% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 749 | Áo thun màu nâu chocolate viền tương phản | Áo thun | Nâu chocolate | 70% Modal, 30% Polyester | Nữ |
| 756 | Áo thun màu nâu cổ cao bất đối xứng | Áo thun | Nâu | 19% Wool Yarn | Nữ |
| 762 | Áo thun màu nâu chocolate gân | Áo thun | Nâu chocolate | 96% Cotton, 4% Sợi co giãn (Elastane) | Nữ |
| 764 | Áo thun màu nâu nhạt tối giản tay ngắn | Áo thun | Nâu nhạt | 100% Cotton | Nữ |
| 768 | Áo thun màu nâu viền tương phản | Áo thun | Nâu | 95% Cotton, 5% Sợi co giãn (Elastane) | Nữ |
| 769 | Áo thun màu nâu chocolate hiệu ứng kép tay ngắn | Áo thun | Nâu chocolate | 100% Cotton | Nữ |
| 774 | Áo thun màu nâu chocolate tay dài vải interlock co giãn | Áo thun | Nâu chocolate | — | Nữ |
| 782 | Áo thun màu nâu chocolate crop tay bồng ngắn | Áo thun | Nâu chocolate | 100% Cotton | Nữ |
| 803 | Áo thun màu nâu tay dài in chữ wash | Áo thun | Nâu | 100% Cotton Yarn | Nữ |
| 804 | Áo thun màu nâu và nâu xám cổ v tay dài buộc eo | Áo thun | Nâu / Nâu xám | 100% Cotton | Nữ |
| 806 | Áo thun màu nâu melange raglan tay ngắn | Áo thun | Nâu melange | 91% Acrylic, 9% Sợi co giãn (Elastane) | Nữ |
| 857 | Áo thun màu nâu và xanh lá lyocell hemp sọc tay ngắn | Áo thun | Nâu / Xanh lá | 87% Lyocell, 13% Gai dầu | Nữ |
| 895 | Áo thun màu nâu sát nách bất đối xứng | Áo thun | Nâu | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |
| 896 | Áo thun màu be và nâu tay ngắn phối vải tương phản | Áo thun | Be / Nâu | 89% Acrylic, 11% Sợi co giãn (Elastane) | Nữ |
| 907 | Áo thun màu nâu đậm dài tay cổ tròn | Áo thun | Nâu đậm | 60% Cotton, 40% Polyester | Nữ |
| 925 | Áo thun màu nâu in hình disney the muppets | Áo thun | Nâu | 50% Cotton, 50% Modal | Nữ |
| 932 | Áo thun màu nâu camel in slogan | Áo thun | Nâu camel | 48% Cotton, 48% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 950 | Áo thun màu nâu sọc thêu tay dài | Áo thun | Nâu sọc | 100% Cotton Yarn | Nữ |
| 953 | Áo thun màu nâu chocolate phối ren | Áo thun | Nâu chocolate | Cotton | Nữ |
| 959 | Áo thun màu nâu chocolate phối voan | Áo thun | Nâu chocolate | 95% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 963 | Áo thun màu nâu và xanh dương raglan phối màu nâu | Áo thun | Nâu / Xanh dương | 96% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 972 | Áo thun màu cát và nâu ba lỗ phong cách rustic | Áo thun | Màu cát / Nâu | 100% Cotton | Nữ |
| 1011 | Áo thun màu nâu melange basic tay ngắn | Áo thun | Nâu melange | 57% Cotton, 38% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 1015 | Áo thun màu nâu chocolate tay ngắn in hình elvis | Áo thun | Nâu chocolate | 100% Cotton | Nữ |

### `conv-rec-0020-t0`

- Session/turn: `conv-rec-0020` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `recommendation`
- Entity IDs: `773`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tôi cần Áo thun màu Trắng cho Nữ, có gợi ý nào không?

**Reference:** Gợi ý các sản phẩm Áo thun phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo thun màu trắng cotton dày tay dài có nơ.

**Must include:** Áo thun

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `708;711;730;746;751;752;753;754;773;797;816;820;822;825;826;828;831;848;858;865;885;886;887;892;893;899;904;906;926;931;939;952;960;964;967;974;977;980;983;988;1003;1013;1470`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-rec-0020-t0-e1 | — | constraint | must_have | category=Áo thun; color=Trắng; gender=Nữ; valid_source_count=43 |
| conv-rec-0020-t0-e2 | 773 | supporting | nice_to_have | color=Trắng |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 773 | Áo thun màu trắng cotton dày tay dài có nơ | Áo thun | Trắng | 100% Compact Cotton | Nữ |
| 708 | Áo thun màu trắng ngà dáng ôm tay dài xuyên thấu | Áo thun | Trắng ngà | 100% Cotton | Nữ |
| 711 | Áo thun màu trắng oversize có túi đắp | Áo thun | Trắng | 100% Cotton Yarn | Nữ |
| 730 | Áo thun màu trắng dáng ôm cổ V gấu bất đối xứng | Áo thun | Trắng | 48% Polyester, 47% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 746 | Áo thun màu trắng tay ngắn xẻ sau | Áo thun | Trắng | 96% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 751 | Áo thun màu trắng thêu tương phản | Áo thun | Trắng | 100% Cotton | Nữ |
| 752 | Áo thun màu trắng và đỏ tay raglan dài phối màu | Áo thun | Trắng / Đỏ | 30% Linen Blend Yarn | Nữ |
| 753 | Áo thun màu trắng ngà và xanh dương tay raglan dài phối màu | Áo thun | Trắng ngà / Xanh dương | 30% Linen Blend | Nữ |
| 754 | Áo thun màu trắng cổ cao bất đối xứng | Áo thun | Trắng | 19% Wool Yarn | Nữ |
| 797 | Áo thun màu trắng ngà tay dài phối hai lớp | Áo thun | Trắng ngà | 20% Len lông cừu | Nữ |
| 816 | Áo thun màu trắng ngà tay dài thêu họa tiết | Áo thun | Trắng ngà | 49% Cotton, 46% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 820 | Áo thun màu trắng ngà tay ngắn vải linen mát mẻ | Áo thun | Trắng ngà | 20% Linen Blend Yarn | Nữ |
| 822 | Áo thun màu trắng ngà linen pha cổ cao không tay | Áo thun | Trắng ngà | 20% Linen Blend Yarn | Nữ |
| 825 | Áo thun màu trắng cổ tim tay dài cotton | Áo thun | Trắng | 93% Cotton, 7% Sợi co giãn (Elastane) | Nữ |
| 826 | Áo thun màu trắng ngà tay dài thêu sau lưng | Áo thun | Trắng ngà | 49% Cotton, 46% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 828 | Áo thun màu trắng ngà không tay sọc linen | Áo thun | Trắng ngà | 8% Linen Blend Yarn | Nữ |
| 831 | Áo thun màu trắng ngà ba lỗ cổ v | Áo thun | Trắng ngà | 48% Modal, 47% Cotton, 5% Sợi co giãn (Elastane) | Nữ |
| 848 | Áo thun màu trắng ngà polyamide dây mảnh dáng ôm | Áo thun | Trắng ngà | 94% Polyamide, 6% Sợi co giãn (Elastane) | Nữ |
| 858 | Áo thun màu trắng cotton tay ngắn bèo nhún | Áo thun | Trắng | 100% Cotton | Nữ |
| 865 | Áo thun màu trắng ngà rách tay ngắn cổ tròn | Áo thun | Trắng ngà | 100% Cotton | Nữ |
| 885 | Áo thun màu trắng ngà linen pha tay ngắn xếp ly | Áo thun | Trắng ngà | 50% Modal, 47% Vải lanh, 3% Sợi co giãn (Elastane) | Nữ |
| 886 | Áo thun màu trắng ngà in hình marvel© mr. fantastic | Áo thun | Trắng ngà | 98% Cotton, 2% Sợi co giãn (Elastane) | Nữ |
| 887 | Áo thun màu trắng thêu hoa chữ | Áo thun | Trắng | 100% Cotton | Nữ |
| 892 | Áo thun màu trắng tay ngắn viền bèo phối màu | Áo thun | Trắng | Cotton | Nữ |
| 893 | Áo thun màu trắng họa tiết hoa tay ngắn | Áo thun | Trắng | 98% Cotton, 2% Sợi co giãn (Elastane) | Nữ |
| 899 | Áo thun màu trắng ngà tay ngắn sequin bất đối xứng | Áo thun | Trắng ngà | 100% Cotton | Nữ |
| 904 | Áo thun màu trắng ngà oversize tay ngắn phối vải | Áo thun | Trắng ngà | Cotton | Nữ |
| 906 | Áo thun màu trắng ngà dài tay cổ tròn | Áo thun | Trắng ngà | 60% Cotton, 40% Polyester | Nữ |
| 926 | Áo thun màu trắng hoa 3d | Áo thun | Trắng | 100% Cotton | Nữ |
| 931 | Áo thun màu trắng ngà và xanh dương sọc co giãn tay ngắn | Áo thun | Trắng ngà / Xanh dương | 90% Viscose, 10% Sợi co giãn (Elastane) | Nữ |
| 939 | Áo thun màu trắng peplum tay bồng | Áo thun | Trắng | 96% Polyester, 4% Sợi co giãn (Elastane) | Nữ |
| 952 | Áo thun màu trắng thêu hoa tay bồng | Áo thun | Trắng | Cotton | Nữ |
| 960 | Áo thun màu trắng ngà thêu chữ tay raglan | Áo thun | Trắng ngà | 100% Slub Knit Cotton | Nữ |
| 964 | Áo thun màu trắng ngà gân cổ tim | Áo thun | Trắng ngà | 90% Viscose, 10% Sợi co giãn (Elastane) | Nữ |
| 967 | Áo thun màu trắng ngà cotton cổ cao tay dài | Áo thun | Trắng ngà | 95% Cotton, 5% Sợi co giãn (Elastane) | Nữ |
| 974 | Áo thun màu đen và trắng gân cổ tròn tay ngắn | Áo thun | Đen / Trắng | 100% Cotton | Nữ |
| 977 | Áo thun màu trắng kem và nâu đậm kẻ sọc ngang cổ Henley cài nút | Áo thun | Trắng kem | Cotton pha | Nữ |
| 980 | Áo thun màu trắng in họa tiết paula grenouille | Áo thun | Trắng | 100% Cotton | Nữ |
| 983 | Áo thun màu trắng cổ tròn không tay họa tiết hoa | Áo thun | Trắng | 94% Cotton, 6% Sợi co giãn (Elastane) | Nữ |
| 988 | Áo thun màu trắng kem kẻ sọc ngang vải cotton-linen tay ngắn | Áo thun | Trắng kem | 50% Cotton, 50% Vải lanh | Nữ |
| 1003 | Áo thun màu trắng cổ tròn tay ngắn thêu nhãn | Áo thun | Trắng | 95% Cotton, 5% Sợi co giãn (Elastane) | Nữ |
| 1013 | Áo thun màu trắng tay dài in hình the muppets disney | Áo thun | Trắng | 100% Cotton | Nữ |
| 1470 | Áo thun màu trắng ngà sọc phong cách rustic | Áo thun | Trắng ngà | 64% Acrylic, 36% Polyamide | Nữ |

## Nhóm `followup_ordinal`

### `conv-ord-0001-t0`

- Session/turn: `conv-ord-0001` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `search_initial`
- Entity IDs: `1784`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tìm Quần dài màu Nâu / Trắng ngà

**Reference:** Gợi ý các sản phẩm Quần dài phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Quần Culotte màu nâu và trắng ngà caro thêu.

**Must include:** Quần dài

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `1745;1746;1749;1752;1755;1765;1766;1767;1781;1782;1784;1785;1795;1806;1809;1819;1821;1830;1841;1846;1850;1856;1857;1863;1869;1873;1875;1878;1900;1901;1902;1903;1909;1910;1912;1918;1922;1923;1925;1926;1937;1942;1943;1951;1954;1964;1965;1974;1976;1982;1984;1988;1990;1991;1993;2004;2006;2009;2010;2014;2015;2016;2017;2022;2024;2025;2026;2027;2031;2032;2033`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-ord-0001-t0-e1 | — | constraint | must_have | category=Quần dài; color=Nâu / Trắng ngà; gender=Nữ; valid_source_count=71 |
| conv-ord-0001-t0-e2 | 1784 | supporting | nice_to_have | color=Nâu / Trắng ngà |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1784 | Quần Culotte màu nâu và trắng ngà caro thêu | Quần dài | Nâu / Trắng ngà | 70% Cotton, 30% Polyester | Nữ |
| 1745 | Quần dài ống rộng màu trắng ngà vải interlock hiệu ứng wash | Quần dài | Trắng ngà | 80% Cotton, 20% Polyester | Nữ |
| 1746 | Quần dài ống rộng màu nâu chồn vải interlock hiệu ứng wash | Quần dài | Nâu chồn | 80% Cotton, 20% Polyester | Nữ |
| 1749 | Quần dài màu xám và nâu vàng dáng phồng họa tiết caro | Quần dài | Xám / Nâu vàng | 63% Polyester, 32% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 1752 | Quần dài ống rộng màu hồng và trắng vải poplin kẻ sọc | Quần dài | Hồng / Trắng | 100% Cotton | Nữ |
| 1755 | Quần dài màu trắng ngà dáng phồng cạp cao xếp ly trước | Quần dài | Trắng ngà | 24% Linen Blend Yarn | Nữ |
| 1765 | Quần sarouel màu xám nâu cạp thun dây rút | Quần dài | Xám nâu | 63% Lyocell, 31% Viscose, 6% Polyamide | Nữ |
| 1766 | Quần dài ống côn màu trắng ngà ly chiết phía trước | Quần dài | Trắng ngà | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1767 | Quần dài ống loe màu nâu và trắng ngà cạp thấp sọc mảnh | Quần dài | Nâu / Trắng ngà | 93% Polyester, 5% Sợi co giãn (Elastane), 2% Viscose | Nữ |
| 1781 | Quần dài ống suông màu trắng ngà hiệu ứng nhung tăm | Quần dài | Trắng ngà | 98% Cotton, 2% Sợi co giãn (Elastane) | Nữ |
| 1782 | Quần dài ống suông màu nâu vân xương cá kèm thắt lưng | Quần dài | Nâu | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1785 | Quần Culotte màu xanh navy và trắng caro thêu | Quần dài | Xanh navy / Trắng | 70% Cotton, 30% Polyester | Nữ |
| 1795 | Quần dài ống rộng màu trắng ngà và đen kẻ sọc kiểu pyjama | Quần dài | Trắng ngà / Đen | Polyester, Viscose, Cotton, Vải lanh pha | Nữ |
| 1806 | Quần dài lửng ôm màu trắng cạp cao đường may nổi | Quần dài | Trắng | 71% Polyester, 22% Viscose, 7% Sợi co giãn (Elastane) | Nữ |
| 1809 | Quần dài ống loe màu trắng ngà vải twill co giãn khóa kim loại | Quần dài | Trắng ngà | 45% Lyocell, 22% Polyamide, 22% Viscose, 5% Vải lanh, 4% Sợi co giãn (Elastane), 2% Cotton | Nữ |
| 1819 | Quần dài ống suông màu trắng ngà đường may nổi phía trước | Quần dài | Trắng ngà | 70% Viscose, 30% Polyester | Nữ |
| 1821 | Quần dài lửng màu nâu đậm ly chiết phía trước kèm thắt lưng | Quần dài | Nâu đậm | 74% Polyester, 20% Viscose, 6% Sợi co giãn (Elastane) | Nữ |
| 1830 | Quần dài ống suông màu nâu chocolate vân nổi cạp dây rút | Quần dài | Nâu chocolate | 99% Polyester, 1% Sợi co giãn (Elastane) | Nữ |
| 1841 | Quần dài ống loe màu nâu melange seamless cạp thun | Quần dài | Nâu melange | 48% Polyamide, 47% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 1846 | Quần dài ống loe màu nâu đậm vải linen pha xẻ gấu | Quần dài | Nâu đậm | 68% Viscose, 30% Vải lanh, 2% Sợi co giãn (Elastane) | Nữ |
| 1850 | Quần sarouel màu nâu nhạt cạp thun dây rút | Quần dài | Nâu nhạt | 75% Viscose, 25% Polyamide | Nữ |
| 1856 | Quần dài ống rộng màu trắng ngà vải poplin cotton cạp dây rút | Quần dài | Trắng ngà | 75% Cotton, 22% Polyamide, 3% Sợi co giãn (Elastane) | Nữ |
| 1857 | Quần dài màu trắng ngà dáng phồng kẻ sọc xếp ly trước | Quần dài | Trắng ngà | 36% Cotton, 35% Polyester, 20% Viscose, 9% Vải lanh | Nữ |
| 1863 | Quần dài ống suông màu trắng và xám cạp thấp kẻ sọc | Quần dài | Trắng / Xám | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1869 | Quần dài ống suông màu trắng ngà vân nổi cạp thun | Quần dài | Trắng ngà | 99% Polyester, 1% Sợi co giãn (Elastane) | Nữ |
| 1873 | Quần Capri màu xanh navy và trắng họa tiết gingham | Quần dài | Xanh navy / Trắng | 66% Polyester, 31% Viscose, 3% Sợi co giãn (Elastane) | Nữ |
| 1875 | Quần dài ống rộng màu trắng ngà khóa kéo ẩn bên hông | Quần dài | Trắng ngà | 55% Cotton, 42% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 1878 | Quần dài ống loe màu trắng cạp cao khóa kéo sau | Quần dài | Trắng | 55% Cotton, 42% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 1900 | Quần dài màu trắng vải nylon cạp phủ lớp | Quần dài | Trắng | 100% Polyamide | Nữ |
| 1901 | Quần dài ống rộng màu nâu vải thô kẻ sọc | Quần dài | Nâu | 70% Polyester, 27% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1902 | Quần dài ống suông màu nâu đậm vải piqué thắt lưng tương phản | Quần dài | Nâu đậm | 98% Polyester, 2% Sợi co giãn (Elastane) | Nữ |
| 1903 | Quần dài ống suông màu trắng ngà vải piqué thắt lưng tương phản | Quần dài | Trắng ngà | 98% Polyester, 2% Sợi co giãn (Elastane) | Nữ |
| 1909 | Quần palazzo màu nâu vân nổi cạp dây rút | Quần dài | Nâu | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |
| 1910 | Quần palazzo màu trắng ngà vân nổi cạp dây rút | Quần dài | Trắng ngà | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |
| 1912 | Quần dài ống loe màu nâu vải interlock mềm cạp thun | Quần dài | Nâu | 75% Cotton, 17% Polyester, 8% Sợi co giãn (Elastane) | Nữ |
| 1918 | Quần dài ống suông màu trắng và xám cạp thấp sọc mảnh | Quần dài | Trắng / Xám | 63% Polyester, 32% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 1922 | Quần dài màu nâu chocolate da lộn giả cạp cao | Quần dài | Nâu chocolate | 93% Polyester, 7% Sợi co giãn (Elastane) | Nữ |
| 1923 | Quần sarong ống suông màu trắng kem và xanh xám kẻ sọc dọc vạt chồng | Quần dài | Trắng kem | 24% Linen Blend Yarn | Nữ |
| 1925 | Quần dài ống barrel màu trắng ngà nhung tăm đường may xoắn | Quần dài | Trắng ngà | 100% Cotton | Nữ |
| 1926 | Quần dài ống loe màu nâu camel túi vá | Quần dài | Nâu camel | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1937 | Quần dài ống loe màu nâu cạp cao túi khóa kéo | Quần dài | Nâu | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1942 | Quần cargo ống suông màu nâu hiệu ứng phai màu | Quần dài | Nâu | 100% Cotton | Nữ |
| 1943 | Quần dài lửng màu nâu melange cạp cao đường may nổi | Quần dài | Nâu melange | 63% Polyester, 31% Viscose, 6% Sợi co giãn (Elastane) | Nữ |
| 1951 | Quần dài ống rộng màu đen và trắng ngà vải bouclé kẻ sọc | Quần dài | Đen / Trắng ngà | 75% Polyester, 22% Viscose, 3% Sợi co giãn (Elastane) | Nữ |
| 1954 | Quần dài màu nâu và nâu xám vải nhăn bo gấu | Quần dài | Nâu / Nâu xám | 77% Polyester, 23% Polyamide | Nữ |
| 1964 | Quần dài ống suông màu nâu melange cạp cao | Quần dài | Nâu melange | 49% Polyester, 31% Viscose, 15% Polyamide, 5% Sợi co giãn (Elastane) | Nữ |
| 1965 | Quần dài ống suông màu nâu đậm hàng cúc kim loại | Quần dài | Nâu đậm | 56% Cotton, 41% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 1974 | Quần jogger màu nâu đậm cạp dây rút bo gấu | Quần dài | Nâu đậm | 68% Viscose, 32% Vải lanh | Nữ |
| 1976 | Quần dài lửng ống loe màu nâu camel pha len đường ly ép | Quần dài | Nâu camel | 45% Len lông cừu, 40% Polyester, 15% Vải lanh | Nữ |
| 1982 | Quần dài màu nâu và xanh dương họa tiết caro ly trước | Quần dài | Nâu / Xanh dương | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1984 | Quần dài ống rộng màu trắng ngà vải cotton | Quần dài | Trắng ngà | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1988 | Quần dài màu nâu vàng nhạt cạp quấn túi nắp cài cúc | Quần dài | Nâu vàng nhạt | 54% Cotton, 39% Polyamide, 7% Sợi co giãn (Elastane) | Nữ |
| 1990 | Quần dài màu nâu chồn pha len ly trước | Quần dài | Nâu chồn | 50% Wool Blend | Nữ |
| 1991 | Quần dài ống loe màu đen và trắng kẻ sọc cạp bản rộng | Quần dài | Đen / Trắng | 79% Cotton, 18% Polyamide, 3% Sợi co giãn (Elastane) | Nữ |
| 1993 | Quần dài ống suông màu trắng ngà jacquard kẻ sọc kiểu pyjama | Quần dài | Trắng ngà | 100% Polyester | Nữ |
| 2004 | Quần dài màu nâu sọc mảnh có quai đai | Quần dài | Nâu sọc | 67% Polyester, 29% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 2006 | Quần dài màu nâu đậm pha len ly trước | Quần dài | Nâu đậm | 15% Len lông cừu | Nữ |
| 2009 | Quần dài ống rộng màu nâu melange ly chiết phía trước | Quần dài | Nâu melange | 66% Polyester, 29% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 2010 | Quần dài màu nâu nhạt vải rủ gấu nhún điều chỉnh | Quần dài | Nâu nhạt | 60% Lyocell, 23% Gai dầu, 17% Cotton | Nữ |
| 2014 | Quần dài ống suông màu nâu chồn lưng vừa | Quần dài | Nâu chồn | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 2015 | Quần baggy màu nâu nhạt cạp thấp chi tiết bất đối xứng | Quần dài | Nâu nhạt | 96% Polyester, 4% Sợi co giãn (Elastane) | Nữ |
| 2016 | Quần Capri màu nâu vàng nhạt sọc mảnh | Quần dài | Nâu vàng nhạt | 63% Polyester, 32% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 2017 | Quần dài ống rộng màu đen và trắng ngà họa tiết houndstooth | Quần dài | Đen / Trắng ngà | 56% Polyester, 42% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 2022 | Quần dài ống loe màu đen và trắng vân nổi cúc hình trái tim | Quần dài | Đen / Trắng | 58% Cotton, 42% Polyester | Nữ |
| 2024 | Quần dài lửng ống loe màu nâu cạp thấp | Quần dài | Nâu | 71% Cotton, 24% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 2025 | Quần dài ống rộng màu đen và trắng ngà vải bouclé chỉ kim tuyến | Quần dài | Đen / Trắng ngà | — | Nữ |
| 2026 | Quần dài ống loe màu nâu đường may nổi hai bên | Quần dài | Nâu | 71% Polyester, 22% Viscose, 7% Sợi co giãn (Elastane) | Nữ |
| 2027 | Quần dài ống loe màu trắng ngà cạp thấp đường may nổi hai bên | Quần dài | Trắng ngà | 71% Polyester, 22% Viscose, 7% Sợi co giãn (Elastane) | Nữ |
| 2031 | Quần dài ống suông màu nâu vải nỉ cạp dây rút | Quần dài | Nâu | Cotton pha | Nữ |
| 2032 | Quần dài ống suông màu nâu cạp cao kèm thắt lưng gấu lật | Quần dài | Nâu | 75% Polyester, 19% Viscose, 6% Sợi co giãn (Elastane) | Nữ |
| 2033 | Quần dài ống suông màu trắng ngà cạp cao kèm thắt lưng gấu lật | Quần dài | Trắng ngà | 75% Polyester, 19% Viscose, 6% Sợi co giãn (Elastane) | Nữ |

### `conv-ord-0002-t0`

- Session/turn: `conv-ord-0002` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `search_initial`
- Entity IDs: `511`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tìm Váy & Đầm màu Xám than

**Reference:** Gợi ý các sản phẩm Váy & Đầm phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Đầm mini suông màu xám than vải mềm thắt lưng giả da.

**Must include:** Váy & Đầm

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `338;343;349;393;412;473;481;497;511;520;525;529`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-ord-0002-t0-e1 | — | constraint | must_have | category=Váy & Đầm; color=Xám than; gender=Nữ; valid_source_count=12 |
| conv-ord-0002-t0-e2 | 511 | supporting | nice_to_have | color=Xám than |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 511 | Đầm mini suông màu xám than vải mềm thắt lưng giả da | Váy & Đầm | Xám than | 77% Polyester, 20% Viscose, 3% Sợi co giãn (Elastane) | Nữ |
| 338 | Đầm midi màu trắng và xám phối lớp buộc nơ | Váy & Đầm | Trắng / Xám | — | Nữ |
| 343 | Đầm midi màu xám và be vân xương cá cổ lọ | Váy & Đầm | Xám / Be | 64% Polyester, 35% Viscose, 1% Sợi co giãn (Elastane) | Nữ |
| 349 | Đầm mini màu xám và be dáng phồng cổ yếm bất đối xứng | Váy & Đầm | Xám / Be | 100% Cotton | Nữ |
| 393 | Đầm midi màu xám tro voan nhăn hở lưng | Váy & Đầm | Xám tro | 70% Cotton, 30% Viscose | Nữ |
| 412 | Đầm midi satin màu xám đậm gấu bất đối xứng | Váy & Đầm | Xám đậm | 100% Polyester | Nữ |
| 473 | Đầm mini màu xám nhạt xếp nếp tay dài kèm đai | Váy & Đầm | Xám nhạt | 95% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 481 | Đầm mini màu xám và be họa tiết caro viền bèo | Váy & Đầm | Xám / Be | 41% Polyester, 32% Cotton, 26% Viscose, 1% Sợi co giãn (Elastane) | Nữ |
| 497 | Đầm midi chữ A màu xám nhạt poplin cotton xếp ly eo | Váy & Đầm | Xám nhạt | 100% Cotton | Nữ |
| 520 | Đầm mini lưới màu xám than đậm phối tương phản hở lưng | Váy & Đầm | Xám than đậm | 95% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 525 | Đầm mini dệt kim màu nâu và nâu xám cổ cao tay phồng | Váy & Đầm | Nâu / Nâu xám | 46% Polyamide, 41% Acrylic, 10% Viscose, 3% Sợi co giãn (Elastane) | Nữ |
| 529 | Đầm midi màu xám trung cổ cao thêu chỉ nổi | Váy & Đầm | Xám trung bình | — | Nữ |

### `conv-ord-0003-t0`

- Session/turn: `conv-ord-0003` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `search_initial`
- Entity IDs: `1062`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tìm Áo hai dây, áo sát nách & áo yếm màu Hồng

**Reference:** Gợi ý các sản phẩm Áo hai dây, áo sát nách & áo yếm phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo sát nách màu hồng gân cúc tương phản.

**Must include:** Áo hai dây, áo sát nách & áo yếm

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `1062;1065;1250;1261;1311;1356;1510;1596;1597;1672;1679`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-ord-0003-t0-e1 | — | constraint | must_have | category=Áo hai dây, áo sát nách & áo yếm; color=Hồng; gender=Nữ; valid_source_count=11 |
| conv-ord-0003-t0-e2 | 1062 | supporting | nice_to_have | color=Hồng |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1062 | Áo sát nách màu hồng gân cúc tương phản | Áo hai dây, áo sát nách & áo yếm | Hồng | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1065 | Áo yếm màu hồng và trắng poplin kẻ sọc | Áo hai dây, áo sát nách & áo yếm | Hồng / Trắng | 100% Cotton | Nữ |
| 1250 | Áo yếm màu hồng kẹo cao su dáng crop viền bèo chấm bi | Áo hai dây, áo sát nách & áo yếm | Hồng kẹo cao su | 100% Polyester | Nữ |
| 1261 | Áo yếm màu hồng phấn sequin hồng nhạt xẻ ngực | Áo hai dây, áo sát nách & áo yếm | Hồng phấn | 100% Polyester | Nữ |
| 1311 | Áo hai dây màu hồng cổ tim nút cài | Áo hai dây, áo sát nách & áo yếm | Hồng | 75% Cotton, 17% Polyester, 8% Sợi co giãn (Elastane) | Nữ |
| 1356 | Áo hai dây màu hồng nhạt nhún hông | Áo hai dây, áo sát nách & áo yếm | Hồng nhạt | 100% Polyester | Nữ |
| 1510 | Áo yếm màu hồng cổ yếm đính đá | Áo hai dây, áo sát nách & áo yếm | Hồng | 96% Polyester, 4% Sợi co giãn (Elastane) | Nữ |
| 1596 | Áo yếm màu hồng cổ yếm vải tuyn hoa văn | Áo hai dây, áo sát nách & áo yếm | Hồng | 90% Polyester, 10% Sợi co giãn (Elastane) | Nữ |
| 1597 | Áo hai dây màu hồng phai bèo nhún bất đối xứng | Áo hai dây, áo sát nách & áo yếm | Hồng phai | 100% Polyester | Nữ |
| 1672 | Áo yếm màu hồng fuchsia cổ yếm đính kim sa hở lưng | Áo hai dây, áo sát nách & áo yếm | Hồng fuchsia | 100% Cotton | Nữ |
| 1679 | Áo yếm màu hồng cổ yếm có thắt lưng | Áo hai dây, áo sát nách & áo yếm | Hồng | 75% Cotton, 20% Viscose, 5% Sợi co giãn (Elastane) | Nữ |

### `conv-ord-0005-t0`

- Session/turn: `conv-ord-0005` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `search_initial`
- Entity IDs: `1015`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tìm Áo thun màu Nâu chocolate

**Reference:** Gợi ý các sản phẩm Áo thun phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo thun màu nâu chocolate tay ngắn in hình elvis.

**Must include:** Áo thun

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `703;718;745;749;756;762;764;768;769;774;782;803;804;806;857;895;896;907;925;932;950;953;959;963;972;1011;1015`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-ord-0005-t0-e1 | — | constraint | must_have | category=Áo thun; color=Nâu chocolate; gender=Nữ; valid_source_count=27 |
| conv-ord-0005-t0-e2 | 1015 | supporting | nice_to_have | color=Nâu chocolate |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1015 | Áo thun màu nâu chocolate tay ngắn in hình elvis | Áo thun | Nâu chocolate | 100% Cotton | Nữ |
| 703 | Áo thun màu nâu dáng ôm tay dài | Áo thun | Nâu | 48% Cotton, 47% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 718 | Áo thun màu nâu thuốc lá tay dài gấu rút dây | Áo thun | Nâu thuốc lá | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 745 | Áo thun màu nâu đậm tay ngắn xẻ sau | Áo thun | Nâu đậm | 96% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 749 | Áo thun màu nâu chocolate viền tương phản | Áo thun | Nâu chocolate | 70% Modal, 30% Polyester | Nữ |
| 756 | Áo thun màu nâu cổ cao bất đối xứng | Áo thun | Nâu | 19% Wool Yarn | Nữ |
| 762 | Áo thun màu nâu chocolate gân | Áo thun | Nâu chocolate | 96% Cotton, 4% Sợi co giãn (Elastane) | Nữ |
| 764 | Áo thun màu nâu nhạt tối giản tay ngắn | Áo thun | Nâu nhạt | 100% Cotton | Nữ |
| 768 | Áo thun màu nâu viền tương phản | Áo thun | Nâu | 95% Cotton, 5% Sợi co giãn (Elastane) | Nữ |
| 769 | Áo thun màu nâu chocolate hiệu ứng kép tay ngắn | Áo thun | Nâu chocolate | 100% Cotton | Nữ |
| 774 | Áo thun màu nâu chocolate tay dài vải interlock co giãn | Áo thun | Nâu chocolate | — | Nữ |
| 782 | Áo thun màu nâu chocolate crop tay bồng ngắn | Áo thun | Nâu chocolate | 100% Cotton | Nữ |
| 803 | Áo thun màu nâu tay dài in chữ wash | Áo thun | Nâu | 100% Cotton Yarn | Nữ |
| 804 | Áo thun màu nâu và nâu xám cổ v tay dài buộc eo | Áo thun | Nâu / Nâu xám | 100% Cotton | Nữ |
| 806 | Áo thun màu nâu melange raglan tay ngắn | Áo thun | Nâu melange | 91% Acrylic, 9% Sợi co giãn (Elastane) | Nữ |
| 857 | Áo thun màu nâu và xanh lá lyocell hemp sọc tay ngắn | Áo thun | Nâu / Xanh lá | 87% Lyocell, 13% Gai dầu | Nữ |
| 895 | Áo thun màu nâu sát nách bất đối xứng | Áo thun | Nâu | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |
| 896 | Áo thun màu be và nâu tay ngắn phối vải tương phản | Áo thun | Be / Nâu | 89% Acrylic, 11% Sợi co giãn (Elastane) | Nữ |
| 907 | Áo thun màu nâu đậm dài tay cổ tròn | Áo thun | Nâu đậm | 60% Cotton, 40% Polyester | Nữ |
| 925 | Áo thun màu nâu in hình disney the muppets | Áo thun | Nâu | 50% Cotton, 50% Modal | Nữ |
| 932 | Áo thun màu nâu camel in slogan | Áo thun | Nâu camel | 48% Cotton, 48% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 950 | Áo thun màu nâu sọc thêu tay dài | Áo thun | Nâu sọc | 100% Cotton Yarn | Nữ |
| 953 | Áo thun màu nâu chocolate phối ren | Áo thun | Nâu chocolate | Cotton | Nữ |
| 959 | Áo thun màu nâu chocolate phối voan | Áo thun | Nâu chocolate | 95% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 963 | Áo thun màu nâu và xanh dương raglan phối màu nâu | Áo thun | Nâu / Xanh dương | 96% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 972 | Áo thun màu cát và nâu ba lỗ phong cách rustic | Áo thun | Màu cát / Nâu | 100% Cotton | Nữ |
| 1011 | Áo thun màu nâu melange basic tay ngắn | Áo thun | Nâu melange | 57% Cotton, 38% Modal, 5% Sợi co giãn (Elastane) | Nữ |

## Nhóm `filter_refinement`

### `conv-flt-0001-t0`

- Session/turn: `conv-flt-0001` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `search_initial`
- Entity IDs: `1943`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tìm Quần dài màu Nâu melange

**Reference:** Gợi ý các sản phẩm Quần dài phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Quần dài lửng màu nâu melange cạp cao đường may nổi.

**Must include:** Quần dài

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `1746;1749;1765;1767;1782;1784;1821;1830;1841;1846;1850;1901;1902;1909;1912;1922;1926;1937;1942;1943;1954;1964;1965;1974;1976;1982;1988;1990;2004;2006;2009;2010;2014;2015;2016;2024;2026;2031;2032`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-flt-0001-t0-e1 | — | constraint | must_have | category=Quần dài; color=Nâu melange; gender=Nữ; valid_source_count=39 |
| conv-flt-0001-t0-e2 | 1943 | supporting | nice_to_have | color=Nâu melange |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1943 | Quần dài lửng màu nâu melange cạp cao đường may nổi | Quần dài | Nâu melange | 63% Polyester, 31% Viscose, 6% Sợi co giãn (Elastane) | Nữ |
| 1746 | Quần dài ống rộng màu nâu chồn vải interlock hiệu ứng wash | Quần dài | Nâu chồn | 80% Cotton, 20% Polyester | Nữ |
| 1749 | Quần dài màu xám và nâu vàng dáng phồng họa tiết caro | Quần dài | Xám / Nâu vàng | 63% Polyester, 32% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 1765 | Quần sarouel màu xám nâu cạp thun dây rút | Quần dài | Xám nâu | 63% Lyocell, 31% Viscose, 6% Polyamide | Nữ |
| 1767 | Quần dài ống loe màu nâu và trắng ngà cạp thấp sọc mảnh | Quần dài | Nâu / Trắng ngà | 93% Polyester, 5% Sợi co giãn (Elastane), 2% Viscose | Nữ |
| 1782 | Quần dài ống suông màu nâu vân xương cá kèm thắt lưng | Quần dài | Nâu | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1784 | Quần Culotte màu nâu và trắng ngà caro thêu | Quần dài | Nâu / Trắng ngà | 70% Cotton, 30% Polyester | Nữ |
| 1821 | Quần dài lửng màu nâu đậm ly chiết phía trước kèm thắt lưng | Quần dài | Nâu đậm | 74% Polyester, 20% Viscose, 6% Sợi co giãn (Elastane) | Nữ |
| 1830 | Quần dài ống suông màu nâu chocolate vân nổi cạp dây rút | Quần dài | Nâu chocolate | 99% Polyester, 1% Sợi co giãn (Elastane) | Nữ |
| 1841 | Quần dài ống loe màu nâu melange seamless cạp thun | Quần dài | Nâu melange | 48% Polyamide, 47% Modal, 5% Sợi co giãn (Elastane) | Nữ |
| 1846 | Quần dài ống loe màu nâu đậm vải linen pha xẻ gấu | Quần dài | Nâu đậm | 68% Viscose, 30% Vải lanh, 2% Sợi co giãn (Elastane) | Nữ |
| 1850 | Quần sarouel màu nâu nhạt cạp thun dây rút | Quần dài | Nâu nhạt | 75% Viscose, 25% Polyamide | Nữ |
| 1901 | Quần dài ống rộng màu nâu vải thô kẻ sọc | Quần dài | Nâu | 70% Polyester, 27% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1902 | Quần dài ống suông màu nâu đậm vải piqué thắt lưng tương phản | Quần dài | Nâu đậm | 98% Polyester, 2% Sợi co giãn (Elastane) | Nữ |
| 1909 | Quần palazzo màu nâu vân nổi cạp dây rút | Quần dài | Nâu | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |
| 1912 | Quần dài ống loe màu nâu vải interlock mềm cạp thun | Quần dài | Nâu | 75% Cotton, 17% Polyester, 8% Sợi co giãn (Elastane) | Nữ |
| 1922 | Quần dài màu nâu chocolate da lộn giả cạp cao | Quần dài | Nâu chocolate | 93% Polyester, 7% Sợi co giãn (Elastane) | Nữ |
| 1926 | Quần dài ống loe màu nâu camel túi vá | Quần dài | Nâu camel | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 1937 | Quần dài ống loe màu nâu cạp cao túi khóa kéo | Quần dài | Nâu | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1942 | Quần cargo ống suông màu nâu hiệu ứng phai màu | Quần dài | Nâu | 100% Cotton | Nữ |
| 1954 | Quần dài màu nâu và nâu xám vải nhăn bo gấu | Quần dài | Nâu / Nâu xám | 77% Polyester, 23% Polyamide | Nữ |
| 1964 | Quần dài ống suông màu nâu melange cạp cao | Quần dài | Nâu melange | 49% Polyester, 31% Viscose, 15% Polyamide, 5% Sợi co giãn (Elastane) | Nữ |
| 1965 | Quần dài ống suông màu nâu đậm hàng cúc kim loại | Quần dài | Nâu đậm | 56% Cotton, 41% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 1974 | Quần jogger màu nâu đậm cạp dây rút bo gấu | Quần dài | Nâu đậm | 68% Viscose, 32% Vải lanh | Nữ |
| 1976 | Quần dài lửng ống loe màu nâu camel pha len đường ly ép | Quần dài | Nâu camel | 45% Len lông cừu, 40% Polyester, 15% Vải lanh | Nữ |
| 1982 | Quần dài màu nâu và xanh dương họa tiết caro ly trước | Quần dài | Nâu / Xanh dương | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 1988 | Quần dài màu nâu vàng nhạt cạp quấn túi nắp cài cúc | Quần dài | Nâu vàng nhạt | 54% Cotton, 39% Polyamide, 7% Sợi co giãn (Elastane) | Nữ |
| 1990 | Quần dài màu nâu chồn pha len ly trước | Quần dài | Nâu chồn | 50% Wool Blend | Nữ |
| 2004 | Quần dài màu nâu sọc mảnh có quai đai | Quần dài | Nâu sọc | 67% Polyester, 29% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 2006 | Quần dài màu nâu đậm pha len ly trước | Quần dài | Nâu đậm | 15% Len lông cừu | Nữ |
| 2009 | Quần dài ống rộng màu nâu melange ly chiết phía trước | Quần dài | Nâu melange | 66% Polyester, 29% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 2010 | Quần dài màu nâu nhạt vải rủ gấu nhún điều chỉnh | Quần dài | Nâu nhạt | 60% Lyocell, 23% Gai dầu, 17% Cotton | Nữ |
| 2014 | Quần dài ống suông màu nâu chồn lưng vừa | Quần dài | Nâu chồn | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 2015 | Quần baggy màu nâu nhạt cạp thấp chi tiết bất đối xứng | Quần dài | Nâu nhạt | 96% Polyester, 4% Sợi co giãn (Elastane) | Nữ |
| 2016 | Quần Capri màu nâu vàng nhạt sọc mảnh | Quần dài | Nâu vàng nhạt | 63% Polyester, 32% Viscose, 5% Sợi co giãn (Elastane) | Nữ |
| 2024 | Quần dài lửng ống loe màu nâu cạp thấp | Quần dài | Nâu | 71% Cotton, 24% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 2026 | Quần dài ống loe màu nâu đường may nổi hai bên | Quần dài | Nâu | 71% Polyester, 22% Viscose, 7% Sợi co giãn (Elastane) | Nữ |
| 2031 | Quần dài ống suông màu nâu vải nỉ cạp dây rút | Quần dài | Nâu | Cotton pha | Nữ |
| 2032 | Quần dài ống suông màu nâu cạp cao kèm thắt lưng gấu lật | Quần dài | Nâu | 75% Polyester, 19% Viscose, 6% Sợi co giãn (Elastane) | Nữ |

### `conv-flt-0002-t0`

- Session/turn: `conv-flt-0002` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `search_initial`
- Entity IDs: `326`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tìm Váy & Đầm màu Đỏ / Trắng

**Reference:** Gợi ý các sản phẩm Váy & Đầm phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Đầm mini màu đỏ và trắng chấm bi cài cúc phía trước.

**Must include:** Váy & Đầm

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `306;312;317;318;326;332;338;345;348;351;362;363;381;385;389;391;395;414;429;438;443;466;469;479;507;513;514;530;534;538;555;562;571;577;585;607;611;633;635;641;644;648;651;657;674;679;692;696`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-flt-0002-t0-e1 | — | constraint | must_have | category=Váy & Đầm; color=Đỏ / Trắng; gender=Nữ; valid_source_count=48 |
| conv-flt-0002-t0-e2 | 326 | supporting | nice_to_have | color=Đỏ / Trắng |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 326 | Đầm mini màu đỏ và trắng chấm bi cài cúc phía trước | Váy & Đầm | Đỏ / Trắng | 100% Viscose | Nữ |
| 306 | Đầm mini màu trắng ngà và đỏ chấm bi trễ vai | Váy & Đầm | Trắng ngà / Đỏ | 98% Cotton, 2% Sợi co giãn (Elastane) | Nữ |
| 312 | Đầm mini màu trắng cổ thuyền xếp ly | Váy & Đầm | Trắng | 48% Cotton, 43% Polyester, 9% Sợi co giãn (Elastane) | Nữ |
| 317 | Đầm mini màu xanh navy và trắng cổ nơ tay phồng | Váy & Đầm | Xanh navy / Trắng | 68% Polyester, 30% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 318 | Đầm midi màu nâu và trắng ngà vân nổi thắt lưng tương phản | Váy & Đầm | Nâu / Trắng ngà | 51% Polyester, 31% Cotton, 18% Viscose | Nữ |
| 332 | Đầm mini màu trắng và hồng vân nổi cổ cao | Váy & Đầm | Trắng / Hồng | 50% Polyester, 47% Cotton, 3% Viscose | Nữ |
| 338 | Đầm midi màu trắng và xám phối lớp buộc nơ | Váy & Đầm | Trắng / Xám | — | Nữ |
| 345 | Đầm mini satin màu trắng cổ yếm xếp nếp kèm đai | Váy & Đầm | Trắng | 100% Polyester | Nữ |
| 348 | Đầm mini poplin màu trắng cổ V tay phồng | Váy & Đầm | Trắng | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 351 | Đầm midi cổ yếm màu trắng ngà xếp nếp cài áo hình vỏ sò | Váy & Đầm | Trắng ngà | 93% Polyamide, 7% Sợi co giãn (Elastane) | Nữ |
| 362 | Đầm midi màu trắng ngà ren cổ tim | Váy & Đầm | Trắng ngà | 49% Polyamide, 43% Polyester, 8% Sợi co giãn (Elastane) | Nữ |
| 363 | Đầm mini màu trắng ngà và vàng kẻ sọc cổ V | Váy & Đầm | Trắng ngà / Vàng | 64% Polyester, 34% Viscose, 2% Sợi co giãn (Elastane) | Nữ |
| 381 | Đầm mini màu trắng ngà dáng phồng vải jacquard tay phồng | Váy & Đầm | Trắng ngà | 56% Polyester, 42% Cotton, 2% Sợi co giãn (Elastane) | Nữ |
| 385 | Đầm mini cúp ngực màu trắng ngà thêu đồng màu | Váy & Đầm | Trắng ngà | 100% Cotton | Nữ |
| 389 | Đầm midi màu trắng ngà trễ vai bèo nổi | Váy & Đầm | Trắng ngà | 100% Polyamide | Nữ |
| 391 | Đầm mini màu trắng ngà phối ren gấu bất đối xứng | Váy & Đầm | Trắng ngà | 100% Polyester | Nữ |
| 395 | Đầm mini cúp ngực màu đen và trắng chấm bi kèm thắt lưng | Váy & Đầm | Đen / Trắng | 95% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 414 | Đầm mini satin màu trắng ngà và đen cổ yếm hở lưng | Váy & Đầm | Trắng ngà / Đen | 100% Polyester | Nữ |
| 429 | Đầm mini cúp ngực màu trắng ngà co giãn | Váy & Đầm | Trắng ngà | 93% Polyamide, 7% Sợi co giãn (Elastane) | Nữ |
| 438 | Đầm mini corset màu trắng ngà đính hoa 3D | Váy & Đầm | Trắng ngà | 77% Polyester, 20% Polyamide, 3% Sợi co giãn (Elastane) | Nữ |
| 443 | Đầm mini xòe màu trắng ngà dây chéo lưng | Váy & Đầm | Trắng ngà | 77% Polyester, 20% Polyamide, 3% Sợi co giãn (Elastane) | Nữ |
| 466 | Đầm mini suông màu đen và trắng ngà vải bouclé kẻ sọc | Váy & Đầm | Đen / Trắng ngà | 75% Polyester, 22% Viscose, 3% Sợi co giãn (Elastane) | Nữ |
| 469 | Đầm midi suông màu trắng dệt kim co giãn khoét vai | Váy & Đầm | Trắng | 77% Polyester, 20% Polyamide, 3% Sợi co giãn (Elastane) | Nữ |
| 479 | Đầm midi suông màu nâu và trắng ngà kẻ sọc kèm thắt lưng | Váy & Đầm | Nâu / Trắng ngà | 49% Viscose, 48% Polyester, 3% Sợi co giãn (Elastane) | Nữ |
| 507 | Đầm mini phồng màu trắng dây buộc viền bèo | Váy & Đầm | Trắng | 65% Cotton, 35% Polyamide | Nữ |
| 513 | Đầm mini màu trắng thêu đồng màu hở lưng | Váy & Đầm | Trắng | 100% Cotton | Nữ |
| 514 | Đầm xòe màu đen và trắng vải dệt nổi cúc kim loại | Váy & Đầm | Đen / Trắng | 58% Cotton, 42% Polyester | Nữ |
| 530 | Đầm midi màu trắng ngà cổ V thắt lưng giả | Váy & Đầm | Trắng ngà | 93% Polyester, 7% Sợi co giãn (Elastane) | Nữ |
| 534 | Đầm midi cotton màu trắng godet tay phồng | Váy & Đầm | Trắng | 100% Cotton | Nữ |
| 538 | Đầm midi màu đen và trắng chấm bi xếp nếp gấu bèo | Váy & Đầm | Đen / Trắng | 95% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 555 | Đầm mini màu trắng ngà và đen cổ vuông đính nơ | Váy & Đầm | Trắng ngà / Đen | 90% Polyester, 10% Sợi co giãn (Elastane) | Nữ |
| 562 | Đầm midi cổ yếm màu trắng ngà và đỏ đô chấm bi vải nhăn | Váy & Đầm | Trắng ngà / Đỏ đô | 100% Polyester | Nữ |
| 571 | Đầm mini màu trắng ngà cổ V dây rút không tay | Váy & Đầm | Trắng ngà | 100% Polyester | Nữ |
| 577 | Đầm mini cổ yếm màu trắng ngà đính nơ gấu phồng | Váy & Đầm | Trắng ngà | 48% Cotton, 43% Polyester, 9% Sợi co giãn (Elastane) | Nữ |
| 585 | Đầm sơ mi mini poplin màu trắng rút eo gấu phồng | Váy & Đầm | Trắng | 100% Cotton | Nữ |
| 607 | Đầm cổ yếm màu trắng dây buộc lưng tương phản | Váy & Đầm | Trắng | 100% Polyester | Nữ |
| 611 | Đầm mini màu trắng linen pha kèm thắt lưng hở lưng | Váy & Đầm | Trắng | 52% Vải lanh, 48% Viscose | Nữ |
| 633 | Đầm mini hai dây màu trắng cổ tim đường may định hình | Váy & Đầm | Trắng | 48% Cotton, 43% Polyester, 9% Sợi co giãn (Elastane) | Nữ |
| 635 | Đầm midi màu trắng ngà xếp ly phối ren gấu xòe | Váy & Đầm | Trắng ngà | 100% Cotton | Nữ |
| 641 | Đầm mini phồng màu trắng ngà và be caro vải tổ ong | Váy & Đầm | Trắng ngà / Be | 96% Polyester, 4% Sợi co giãn (Elastane) | Nữ |
| 644 | Đầm mini màu trắng ngà và xanh dương họa tiết hoa cổ tim | Váy & Đầm | Trắng ngà / Xanh dương | 98% Cotton, 2% Sợi co giãn (Elastane) | Nữ |
| 648 | Đầm mini ôm màu đen và trắng chấm bi đính nơ | Váy & Đầm | Đen / Trắng | 97% Cotton, 3% Sợi co giãn (Elastane) | Nữ |
| 651 | Đầm midi màu trắng phối ren tương phản gấu bất đối xứng | Váy & Đầm | Trắng | 100% Polyester | Nữ |
| 657 | Đầm mini màu trắng ngà dáng phồng lót quần short | Váy & Đầm | Trắng ngà | 48% Cotton, 43% Polyester, 9% Sợi co giãn (Elastane) | Nữ |
| 674 | Đầm mini sequin màu trắng hở lưng đai nơ tương phản | Váy & Đầm | Trắng | 95% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 679 | Đầm mini poplin màu trắng bèo dập nổi gấu phồng | Váy & Đầm | Trắng | 100% Cotton | Nữ |
| 692 | Đầm mini quấn màu trắng ngà vải dệt nổi viền bèo | Váy & Đầm | Trắng ngà | 100% Cotton | Nữ |
| 696 | Đầm mini màu trắng ngà và be caro phối chiffon viền bèo | Váy & Đầm | Trắng ngà / Be | 100% Cotton Yarn | Nữ |

### `conv-flt-0003-t0`

- Session/turn: `conv-flt-0003` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `search_initial`
- Entity IDs: `1580`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tìm Áo hai dây, áo sát nách & áo yếm màu Nâu

**Reference:** Gợi ý các sản phẩm Áo hai dây, áo sát nách & áo yếm phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo hai dây màu nâu voan thêu cổ v sâu.

**Must include:** Áo hai dây, áo sát nách & áo yếm

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `1020;1059;1078;1119;1137;1228;1342;1386;1417;1551;1561;1580;1721`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-flt-0003-t0-e1 | — | constraint | must_have | category=Áo hai dây, áo sát nách & áo yếm; color=Nâu; gender=Nữ; valid_source_count=13 |
| conv-flt-0003-t0-e2 | 1580 | supporting | nice_to_have | color=Nâu |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1580 | Áo hai dây màu nâu voan thêu cổ v sâu | Áo hai dây, áo sát nách & áo yếm | Nâu | 100% Cotton | Nữ |
| 1020 | Áo sát nách màu nâu chocolate cotton cổ cao | Áo hai dây, áo sát nách & áo yếm | Nâu chocolate | 96% Cotton, 4% Sợi co giãn (Elastane) | Nữ |
| 1059 | Áo sát nách màu nâu melange cổ tròn hở lưng | Áo hai dây, áo sát nách & áo yếm | Nâu melange | 97% Acrylic, 3% Sợi co giãn (Elastane) | Nữ |
| 1078 | Áo hai dây màu nâu và trắng sọc cổ V | Áo hai dây, áo sát nách & áo yếm | Nâu / Trắng | 64% Lyocell, 34% Cotton, 2% Sợi co giãn (Elastane) | Nữ |
| 1119 | Áo sát nách màu nâu chocolate gân cotton | Áo hai dây, áo sát nách & áo yếm | Nâu chocolate | 58% Cotton, 38% Polyester, 4% Sợi co giãn (Elastane) | Nữ |
| 1137 | Áo hai dây màu trắng ngà và nâu phối vải thêu | Áo hai dây, áo sát nách & áo yếm | Trắng ngà / Nâu | 50% Polyester, 31% Cotton, 18% Viscose, 1% Sợi co giãn (Elastane) | Nữ |
| 1228 | Áo yếm màu nâu họa tiết chấm bi lưng hở | Áo hai dây, áo sát nách & áo yếm | Nâu | 96% Viscose, 4% Sợi co giãn (Elastane) | Nữ |
| 1342 | Áo hai dây màu nâu nhạt polyamide | Áo hai dây, áo sát nách & áo yếm | Nâu nhạt | 60% Polyamide, 40% Sợi co giãn (Elastane) | Nữ |
| 1386 | Áo sát nách màu nâu chocolate giả da lộn cổ vuông | Áo hai dây, áo sát nách & áo yếm | Nâu chocolate | 93% Polyester, 7% Sợi co giãn (Elastane) | Nữ |
| 1417 | Áo sát nách màu nâu chocolate bất đối xứng viền tua rua | Áo hai dây, áo sát nách & áo yếm | Nâu chocolate | 56% Polyester, 43% Cotton, 1% Sợi co giãn (Elastane) | Nữ |
| 1551 | Áo hai dây màu nâu tay phồng cổ vuông | Áo hai dây, áo sát nách & áo yếm | Nâu | 83% Modal, 17% Polyester | Nữ |
| 1561 | Áo yếm màu nâu đậm vải lanh lưng trần | Áo hai dây, áo sát nách & áo yếm | Nâu đậm | 68% Viscose, 30% Vải lanh, 2% Sợi co giãn (Elastane) | Nữ |
| 1721 | Áo hai dây màu nâu voan cổ v lót ngực | Áo hai dây, áo sát nách & áo yếm | Nâu | 100% Viscose | Nữ |

### `conv-flt-0004-t0`

- Session/turn: `conv-flt-0004` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `search_initial`
- Entity IDs: `1656`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`needs_revision`
- Review warnings: `—`

**Question:** Tìm Áo kiểu màu Xanh dương nhạt

**Reference:** Gợi ý các sản phẩm Áo kiểu phù hợp nhu cầu, nêu tối đa 3 lựa chọn mạnh nhất kèm lý do dựa trên danh mục, màu sắc, chất liệu và giới tính. Ví dụ phù hợp: Áo kiểu màu xanh dương nhạt và xanh lá đậm lệch vai kẻ sọc bất đối xứng.

**Must include:** Áo kiểu

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `96;1322;1325;1381;1429;1499;1554;1641;1656;1714`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-flt-0004-t0-e1 | — | constraint | must_have | category=Áo kiểu; color=Xanh dương nhạt; gender=Nữ; valid_source_count=10 |
| conv-flt-0004-t0-e2 | 1656 | supporting | nice_to_have | color=Xanh dương nhạt |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1656 | Áo kiểu màu xanh dương nhạt và xanh lá đậm lệch vai kẻ sọc bất đối xứng | Áo kiểu | Xanh dương nhạt | 30% Linen Blend Yarn | Nữ |
| 96 | Áo kiểu màu xanh dương nhạt bèo nơ xanh nhạt | Áo kiểu | Xanh dương nhạt | 82% Viscose, 18% Polyamide | Nữ |
| 1322 | Áo kiểu màu xanh dương trung bình lệch vai giả da lộn cổ ngang | Áo kiểu | Xanh dương trung bình | 93% Polyester, 7% Sợi co giãn (Elastane) | Nữ |
| 1325 | Áo kiểu màu xanh dương trung bình lệch vai giả da lộn cổ ngang | Áo kiểu | Xanh dương trung bình | 93% Polyester, 7% Sợi co giãn (Elastane) | Nữ |
| 1381 | Áo kiểu màu xanh dương tay phồng khoét lưng | Áo kiểu | Xanh dương | 95% Polyester, 5% Sợi co giãn (Elastane) | Nữ |
| 1429 | Áo kiểu màu xanh dương nhạt trễ vai tay dài đính khóa kim loại | Áo kiểu | Xanh dương nhạt | 54% Polyester, 45% Viscose, 1% Sợi co giãn (Elastane) | Nữ |
| 1499 | Áo kiểu màu xanh dương vải lanh pha xếp ly | Áo kiểu | Xanh dương | 54% Vải lanh, 44% Cotton, 2% Sợi co giãn (Elastane) | Nữ |
| 1554 | Áo kiểu màu xanh dương nhạt dáng quây vải dệt nổi cổ ngang | Áo kiểu | Xanh dương nhạt | 98% Polyester, 2% Sợi co giãn (Elastane) | Nữ |
| 1641 | Áo kiểu màu trắng ngà và xanh dương hai dây caro smocked | Áo kiểu | Trắng ngà / Xanh dương | 72% Polyester, 27% Cotton, 1% Sợi co giãn (Elastane) | Nữ |
| 1714 | Áo kiểu màu nâu và xanh dương kẻ tay bồng nâu xanh | Áo kiểu | Nâu / Xanh dương | 87% Cotton, 12% Polyester, 1% Lyocell | Nữ |

## Nhóm `shop_knowledge`

### `conv-shop-0007-t0`

- Session/turn: `conv-shop-0007` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `shipping_fee_policy`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Shop có freeship cho đơn dưới 100k không?

**Reference:** Shop miễn phí vận chuyển từ 500.000đ tại nội thành Hà Nội/TP.HCM hoặc từ 1.000.000đ toàn quốc theo điều kiện công bố; đơn dưới 100.000đ không đạt ngưỡng freeship.

**Must include:** 500.000đ;1.000.000đ;đơn dưới 100.000đ

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-shop-0007-t0-e1 | — | constraint | must_have | Shop miễn phí vận chuyển từ 500.000đ tại nội thành Hà Nội/TP.HCM hoặc từ 1.000.000đ toàn quốc theo điều kiện công bố; đơn dưới 100.000đ không đạt ngưỡng freeship. |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `conv-shop-0005-t0`

- Session/turn: `conv-shop-0005` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `payment_methods`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Thanh toán bằng phương thức nào?

**Reference:** Mystery Closet hỗ trợ COD, chuyển khoản ngân hàng, thẻ Visa/MasterCard/JCB, ví MoMo/ZaloPay/VNPay và QR Code.

**Must include:** COD;chuyển khoản;Visa;MoMo

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-shop-0005-t0-e1 | — | constraint | must_have | Mystery Closet hỗ trợ COD, chuyển khoản ngân hàng, thẻ Visa/MasterCard/JCB, ví MoMo/ZaloPay/VNPay và QR Code. |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `conv-shop-0008-t0`

- Session/turn: `conv-shop-0008` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `warranty_policy`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Sản phẩm của shop được bảo hành trong bao lâu?

**Reference:** Quần áo và phụ kiện được bảo hành 30 ngày, giày dép được bảo hành 60 ngày kể từ ngày mua, trong phạm vi điều kiện bảo hành của Mystery Closet.

**Must include:** 30 ngày;60 ngày

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-shop-0008-t0-e1 | — | constraint | must_have | Quần áo và phụ kiện được bảo hành 30 ngày, giày dép được bảo hành 60 ngày kể từ ngày mua, trong phạm vi điều kiện bảo hành của Mystery Closet. |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `conv-shop-0002-t0`

- Session/turn: `conv-shop-0002` / `0`
- Difficulty/history: `easy` / `false`
- Expected type: `catalog_overview`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Shop hiện tại đang bán những loại sản phẩm nào?

**Reference:** Theo catalog snapshot hiện tại, shop có 15 loại sản phẩm đang bán: Váy & đầm (192), Áo kiểu (154), Quần dài (153), Áo thun (153), Áo hai dây, áo sát nách & áo yếm (128), Áo sơ mi (102), Áo dệt kim & cardigan (60), Bodysuit (31), Blazer & áo vest (15), Jumpsuit & áo liền quần (7), Chân váy (1), Quần jeans (1), Quần legging (1), Quần short (1), Áo khoác (1). Không được tự thêm danh mục không xuất hiện trong catalog.

**Must include:** Váy & đầm;Áo kiểu;Quần dài;Áo thun;Áo hai dây, áo sát nách & áo yếm

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| ví da \| túi xách \| balo \| giày dép \| phụ kiện thời trang

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-shop-0002-t0-e1 | — | constraint | must_have | active catalog category counts: Váy & đầm (192), Áo kiểu (154), Quần dài (153), Áo thun (153), Áo hai dây, áo sát nách & áo yếm (128), Áo sơ mi (102), Áo dệt kim & cardigan (60), Bodysuit (31), Blazer & áo vest (15), Jumpsuit & áo liền quần (7), Chân váy (1), Quần jeans (1), Quần legging (1), Quần short (1), Áo khoác (1) |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `conv-shop-0003-t0`

- Session/turn: `conv-shop-0003` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `shipping_time_policy`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Đơn hàng được giao trong bao lâu?

**Reference:** Đơn được xử lý trong 24 giờ làm việc. Sau khi bàn giao, thời gian dự kiến là 1-2 ngày làm việc ở nội thành Hà Nội/TP.HCM, 3-5 ngày ở tỉnh thành khác và 5-7 ngày tại miền núi, hải đảo.

**Must include:** 1-2 ngày;3-5 ngày;5-7 ngày

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-shop-0003-t0-e1 | — | constraint | must_have | Đơn được xử lý trong 24 giờ làm việc. Sau khi bàn giao, thời gian dự kiến là 1-2 ngày làm việc ở nội thành Hà Nội/TP.HCM, 3-5 ngày ở tỉnh thành khác và 5-7 ngày tại miền núi, hải đảo. |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `conv-shop-0001-t0`

- Session/turn: `conv-shop-0001` / `0`
- Difficulty/history: `easy` / `false`
- Expected type: `shop_identity_and_location`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Shop hiện tại có tên là gì? Cho tôi vị trí của shop được không?

**Reference:** Shop có tên là Mystery Closet (trang giới thiệu dùng tên Mystery Closet Store). Địa chỉ shop là 260 Lý Thường Kiệt, Phường 14, Quận 10, TP. HCM, Việt Nam.

**Must include:** Mystery Closet;260 Lý Thường Kiệt;Quận 10;TP. HCM

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-shop-0001-t0-e1 | — | constraint | must_have | Footer: Mystery Closet; địa chỉ 260 Lý Thường Kiệt, Phường 14, Quận 10, TP. HCM |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `conv-shop-0004-t0`

- Session/turn: `conv-shop-0004` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `return_policy`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Tôi có thể đổi trả sản phẩm trong mấy ngày?

**Reference:** Khách hàng có thể yêu cầu đổi trả trong 07 ngày kể từ ngày nhận hàng nếu sản phẩm còn tem nhãn, chưa sử dụng/giặt ủi và đủ điều kiện theo chính sách.

**Must include:** 07 ngày

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-shop-0004-t0-e1 | — | constraint | must_have | Khách hàng có thể yêu cầu đổi trả trong 07 ngày kể từ ngày nhận hàng nếu sản phẩm còn tem nhãn, chưa sử dụng/giặt ủi và đủ điều kiện theo chính sách. |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `conv-shop-0006-t0`

- Session/turn: `conv-shop-0006` / `0`
- Difficulty/history: `medium` / `false`
- Expected type: `express_shipping_policy`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Shop có giao trong 10 phút không?

**Reference:** Shop có giao hỏa tốc trong ngày tại nội thành Hà Nội và TP.HCM, phí từ 50.000đ đến 100.000đ. Chính sách không công bố dịch vụ giao trong 10 phút.

**Must include:** hỏa tốc trong ngày;Hà Nội;TP.HCM;không công bố dịch vụ giao trong 10 phút

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-shop-0006-t0-e1 | — | constraint | must_have | Shop có giao hỏa tốc trong ngày tại nội thành Hà Nội và TP.HCM, phí từ 50.000đ đến 100.000đ. Chính sách không công bố dịch vụ giao trong 10 phút. |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

## Nhóm `unanswerable`

### `conv-una-v2-0002-t0`

- Session/turn: `conv-una-v2-0002` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `refusal`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Áo kiểu màu đỏ không tay xếp ly trước có được người nổi tiếng nào mặc chưa?

**Reference:** Hiện tại shop chưa hỗ trợ thông tin này trong hệ thống tư vấn. Em xin phép chưa thể trả lời chắc chắn; anh/chị vui lòng kiểm tra trang chính sách của shop hoặc liên hệ CSKH để được hỗ trợ.

**Must include:** chưa hỗ trợ

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| bịa chính sách vận chuyển/đổi trả/thanh toán chưa có trong hệ thống \| cam kết sai về công dụng sản phẩm

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-una-v2-0002-t0-e1 | — | constraint | must_have | Không có dữ liệu catalog/footer/chính sách để xác nhận tuyên bố trong câu hỏi. |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `conv-una-v2-0001-t0`

- Session/turn: `conv-una-v2-0001` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `refusal`
- Entity IDs: `—`
- Trạng thái: question=`pending`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Sản phẩm này có chắc chắn giúp tôi trông cao hơn không?

**Reference:** Hiện tại shop chưa hỗ trợ thông tin này trong hệ thống tư vấn. Em xin phép chưa thể trả lời chắc chắn; anh/chị vui lòng kiểm tra trang chính sách của shop hoặc liên hệ CSKH để được hỗ trợ.

**Must include:** chưa hỗ trợ

**Must not include:** bịa product_id không có trong danh sách trả về \| khẳng định tồn kho / còn hàng / hết hàng khi context không có \| khẳng định giá cuối hoặc mức giảm giá khi context không có \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| bịa chính sách vận chuyển/đổi trả/thanh toán chưa có trong hệ thống \| cam kết sai về công dụng sản phẩm

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| conv-una-v2-0001-t0-e1 | — | constraint | must_have | Không có dữ liệu catalog/footer/chính sách để xác nhận tuyên bố trong câu hỏi. |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

## Nhóm `critical_price`

### `critical-price-001`

- Session/turn: `critical-price-001` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `price`
- Entity IDs: `1035`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Sản phẩm Bodysuit màu đen cổ tim gọng nâng phối tương phản hiện có giá bao nhiêu?

**Reference:** Giá hiện tại của Bodysuit màu đen cổ tim gọng nâng phối tương phản là 579.000 VND. Giá gốc là 599.000 VND.

**Must include:** giá hiện tại \| VND

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| nêu giá không có trong context

**Reference source IDs:** `1035`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-price-001-e1 | 1035 | primary | must_have | effective_price=579000.0; price=599000.0; discounted_price=579000.0 |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1035 | Bodysuit màu đen cổ tim gọng nâng phối tương phản | Bodysuit | Đen | 100% Cotton | Nữ |

### `critical-price-002`

- Session/turn: `critical-price-002` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `price`
- Entity IDs: `1903`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Sản phẩm Quần dài ống suông màu trắng ngà vải piqué thắt lưng tương phản hiện có giá bao nhiêu?

**Reference:** Giá hiện tại của Quần dài ống suông màu trắng ngà vải piqué thắt lưng tương phản là 779.000 VND. Giá gốc là 799.000 VND.

**Must include:** giá hiện tại \| VND

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| nêu giá không có trong context

**Reference source IDs:** `1903`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-price-002-e1 | 1903 | primary | must_have | effective_price=779000.0; price=799000.0; discounted_price=779000.0 |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1903 | Quần dài ống suông màu trắng ngà vải piqué thắt lưng tương phản | Quần dài | Trắng ngà | 98% Polyester, 2% Sợi co giãn (Elastane) | Nữ |

### `critical-price-003`

- Session/turn: `critical-price-003` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `price`
- Entity IDs: `672`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Sản phẩm Đầm sơ mi mini màu cát cotton kèm thắt lưng xẻ hông hiện có giá bao nhiêu?

**Reference:** Giá hiện tại của Đầm sơ mi mini màu cát cotton kèm thắt lưng xẻ hông là 1.079.000 VND. Giá gốc là 1.099.000 VND.

**Must include:** giá hiện tại \| VND

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| nêu giá không có trong context

**Reference source IDs:** `672`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-price-003-e1 | 672 | primary | must_have | effective_price=1079000.0; price=1099000.0; discounted_price=1079000.0 |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 672 | Đầm sơ mi mini màu cát cotton kèm thắt lưng xẻ hông | Váy & Đầm | Màu cát | 98% Cotton, 2% Sợi co giãn (Elastane) | Nữ |

### `critical-price-004`

- Session/turn: `critical-price-004` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `price`
- Entity IDs: `686`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Sản phẩm Đầm mini phồng màu đen gấu bo chun hiện có giá bao nhiêu?

**Reference:** Giá hiện tại của Đầm mini phồng màu đen gấu bo chun là 779.000 VND. Giá gốc là 799.000 VND.

**Must include:** giá hiện tại \| VND

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| nêu giá không có trong context

**Reference source IDs:** `686`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-price-004-e1 | 686 | primary | must_have | effective_price=779000.0; price=799000.0; discounted_price=779000.0 |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 686 | Đầm mini phồng màu đen gấu bo chun | Váy & Đầm | Đen | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |

## Nhóm `critical_stock`

### `critical-stock-001`

- Session/turn: `critical-stock-001` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `availability`
- Entity IDs: `1035`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Bodysuit màu đen cổ tim gọng nâng phối tương phản size M còn hàng không?

**Reference:** Có, Bodysuit màu đen cổ tim gọng nâng phối tương phản size M hiện còn hàng.

**Must include:** size M \| còn hàng

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| suy tồn kho size từ total_stock

**Reference source IDs:** `1035`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-stock-001-e1 | 1035 | primary | must_have | size=M; available=True; active=True; inventory_count=50 |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1035 | Bodysuit màu đen cổ tim gọng nâng phối tương phản | Bodysuit | Đen | 100% Cotton | Nữ |

### `critical-stock-002`

- Session/turn: `critical-stock-002` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `availability`
- Entity IDs: `1903`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Quần dài ống suông màu trắng ngà vải piqué thắt lưng tương phản size L còn hàng không?

**Reference:** Có, Quần dài ống suông màu trắng ngà vải piqué thắt lưng tương phản size L hiện còn hàng.

**Must include:** size L \| còn hàng

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| suy tồn kho size từ total_stock

**Reference source IDs:** `1903`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-stock-002-e1 | 1903 | primary | must_have | size=L; available=True; active=True; inventory_count=50 |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1903 | Quần dài ống suông màu trắng ngà vải piqué thắt lưng tương phản | Quần dài | Trắng ngà | 98% Polyester, 2% Sợi co giãn (Elastane) | Nữ |

### `critical-stock-003`

- Session/turn: `critical-stock-003` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `availability`
- Entity IDs: `1823`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Quần dài ống rộng màu xanh dương cạp cao vạt chồng size XS còn hàng không?

**Reference:** Có, Quần dài ống rộng màu xanh dương cạp cao vạt chồng size XS hiện còn hàng.

**Must include:** size XS \| còn hàng

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| suy tồn kho size từ total_stock

**Reference source IDs:** `1823`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-stock-003-e1 | 1823 | primary | must_have | size=XS; available=True; active=True; inventory_count=50 |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 1823 | Quần dài ống rộng màu xanh dương cạp cao vạt chồng | Quần dài | Xanh dương | 58% Polyester, 38% Viscose, 4% Sợi co giãn (Elastane) | Nữ |

### `critical-stock-004`

- Session/turn: `critical-stock-004` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `availability`
- Entity IDs: `686`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Đầm mini phồng màu đen gấu bo chun size S còn hàng không?

**Reference:** Có, Đầm mini phồng màu đen gấu bo chun size S hiện còn hàng.

**Must include:** size S \| còn hàng

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| suy tồn kho size từ total_stock

**Reference source IDs:** `686`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-stock-004-e1 | 686 | primary | must_have | size=S; available=True; active=True; inventory_count=50 |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| 686 | Đầm mini phồng màu đen gấu bo chun | Váy & Đầm | Đen | 94% Polyester, 6% Sợi co giãn (Elastane) | Nữ |

## Nhóm `critical_product`

### `critical-product-001`

- Session/turn: `critical-product-001` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `unanswerable`
- Entity IDs: `—`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Shop có Áo khoác Sao Hỏa phiên bản 2099 không? Nếu không có dữ liệu hãy nói rõ.

**Reference:** Không, shop không tìm thấy Áo khoác Sao Hỏa phiên bản 2099 trong danh mục hiện tại. Shop có thể gợi ý riêng các sản phẩm tương tự nếu bạn muốn.

**Must include:** không tìm thấy \| Sao Hỏa

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| khẳng định sản phẩm được hỏi tồn tại

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-product-001-e1 | — | constraint | must_have | Normalized exact title/product-code lookup returns no catalog product; semantic neighbors may only be labeled as optional similar suggestions |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `critical-product-002`

- Session/turn: `critical-product-002` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `unanswerable`
- Entity IDs: `—`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Cho tôi thông tin sản phẩm Váy Mặt Trăng mã MC-999999; nếu không tìm thấy hãy nói rõ.

**Reference:** Không, shop không tìm thấy mã MC-999999 trong danh mục hiện tại. Shop có thể gợi ý riêng các sản phẩm tương tự nếu bạn muốn.

**Must include:** không tìm thấy \| MC-999999

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| khẳng định sản phẩm được hỏi tồn tại

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-product-002-e1 | — | constraint | must_have | Normalized exact title/product-code lookup returns no catalog product; semantic neighbors may only be labeled as optional similar suggestions |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

## Nhóm `critical_policy`

### `critical-policy-001`

- Session/turn: `critical-policy-001` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `unanswerable`
- Entity IDs: `—`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Shop có cam kết bảo hành trọn đời cho mọi sản phẩm không? Nếu không có dữ liệu hãy nói rõ.

**Reference:** Không, shop không có cam kết bảo hành trọn đời. Theo Chính sách bảo hành của Mystery Closet: quần áo và phụ kiện được bảo hành 30 ngày, giày dép 60 ngày kể từ ngày mua. Phạm vi gồm lỗi đường may, nút/khóa, bạc màu hoặc co rút/xù lông bất thường trong điều kiện sử dụng và bảo quản bình thường; kết quả kiểm tra được thông báo trong 3-5 ngày làm việc.

**Must include:** Không \| 30 ngày \| 60 ngày

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| khẳng định bảo hành trọn đời

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-policy-001-e1 | — | constraint | must_have | Official footer-aligned policy: clothing warranty 30 days; footwear warranty 60 days; no lifetime-warranty commitment |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

### `critical-policy-002`

- Session/turn: `critical-policy-002` / `0`
- Difficulty/history: `hard` / `false`
- Expected type: `unanswerable`
- Entity IDs: `—`
- Trạng thái: question=`approved`, reference=`pending`, evidence=`pending`
- Review warnings: `—`

**Question:** Shop có cam kết hoàn tiền 200 phần trăm trong mọi trường hợp không? Nếu không có dữ liệu hãy nói rõ.

**Reference:** Không, shop không có cam kết hoàn tiền 200% trong mọi trường hợp. Theo Chính sách đổi trả, bạn có thể yêu cầu đổi trả trong 07 ngày kể từ ngày nhận hàng nếu sản phẩm còn tem nhãn, chưa sử dụng/giặt ủi, không hư hỏng do người dùng và có thể xác minh việc mua hàng. Mỗi đơn được đổi trả 01 lần; hàng giảm trên 30% chỉ được đổi size nếu còn hàng và không áp dụng trả hàng hoàn tiền.

**Must include:** Không \| 07 ngày

**Must not include:** bịa product_id không có trong danh sách trả về \| lộ thuật ngữ kỹ thuật: RAG, embedding, vector, API, database, JSON, system prompt \| khẳng định hoàn tiền 200%

**Reference source IDs:** `—`

**Evidence:**

| Evidence ID | Source | Role | Level | Text |
|---|---|---|---|---|
| critical-policy-002-e1 | — | constraint | must_have | Official footer-aligned return policy: eligible requests within 07 days; no unconditional 200% refund commitment |

**Source products:**

| ID | Tên | Category | Color | Material | Gender |
|---|---|---|---|---|---|
| — | Không có source product | — | — | — | — |

