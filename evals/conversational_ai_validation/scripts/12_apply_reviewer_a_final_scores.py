from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = (
    ROOT
    / "baselines"
    / "rag_memory_rerank_on_post_fix"
    / "review"
)
PACKET = REVIEW_DIR / "reviewer_a_final.csv"
SUMMARY = REVIEW_DIR / "REVIEWER_A_SCORES_FINAL.md"

RATING_FIELDS = (
    "factual_correctness",
    "groundedness",
    "answer_relevancy",
    "completeness",
    "task_success",
    "context_retention",
    "refusal_correctness",
    "helpfulness",
)
GATE_FIELDS = (
    "critical_price",
    "critical_stock",
    "critical_product_exists",
    "critical_policy",
    "critical_clarification_or_refusal",
)


def score(
    factual: int,
    grounded: int,
    relevant: int,
    complete: int,
    task: int | str,
    context: int | str,
    refusal: int | str,
    helpful: int,
    note: str,
    *,
    price: str = "NA",
    stock: str = "NA",
    product: str = "pass",
    policy: str = "NA",
    clarification: str = "NA",
) -> dict[str, str]:
    values = (
        factual,
        grounded,
        relevant,
        complete,
        task,
        context,
        refusal,
        helpful,
        price,
        stock,
        product,
        policy,
        clarification,
    )
    return {
        **{field: str(value) for field, value in zip(RATING_FIELDS + GATE_FIELDS, values)},
        "review_notes": f"[Reviewer A hậu sửa] {note}",
    }


ALL_5 = (5, 5, 5, 5, 5, "NA", "NA", 5)
ALL_5_CONTEXT = (5, 5, 5, 5, 5, 5, "NA", 5)

SCORES: dict[str, dict[str, str]] = {
    # Critical product: từ chối trước, sau đó mới gợi ý sản phẩm có trong context.
    "critical-product-001": score(
        5, 5, 4, 5, "NA", "NA", 5, 4,
        "Từ chối đúng sản phẩm không tồn tại trước khi gợi ý. Một áo khoác phù hợp; hai gợi ý áo kiểu hơi xa nhu cầu nên relevancy/helpfulness=4.",
        clarification="pass",
    ),
    "critical-product-002": score(
        5, 5, 5, 5, "NA", "NA", 5, 5,
        "Từ chối đúng mã không tồn tại; ba gợi ý thay thế đều là Váy & Đầm có trong context.",
        clarification="pass",
    ),

    # Filter refinement.
    "conv-flt-0001-t0": score(*ALL_5, "Ba quần dài đều đúng màu Nâu melange và đúng evidence."),
    "conv-flt-0001-t1": score(*ALL_5_CONTEXT, "Giữ đúng danh mục Quần dài và thay màu sang Đen; cả ba kết quả phù hợp."),
    "conv-flt-0002-t0": score(*ALL_5, "Ba đầm đều mang tổ hợp đỏ/trắng hoặc biến thể trắng ngà/đỏ phù hợp."),
    "conv-flt-0002-t1": score(*ALL_5_CONTEXT, "Giữ đúng danh mục và màu tổ hợp; thông báo không có mẫu rẻ hơn thay vì đưa kết quả sai giá."),
    "conv-flt-0003-t0": score(*ALL_5, "Ba sản phẩm đúng danh mục áo hai dây/sát nách/yếm và màu Nâu."),
    "conv-flt-0003-t1": score(
        5, 5, 4, 4, 4, 4, "NA", 4,
        "Giữ đúng danh mục; hai mẫu Trắng khớp hoàn toàn, mẫu thứ ba Trắng ngà chỉ gần màu yêu cầu.",
    ),
    "conv-flt-0004-t0": score(*ALL_5, "Ba áo kiểu đều có màu Xanh dương nhạt và đúng evidence."),
    "conv-flt-0004-t1": score(*ALL_5_CONTEXT, "Giữ đúng danh mục Áo kiểu và chuyển sang các mẫu có màu Đen."),
    "conv-flt-0005-t0": score(*ALL_5, "Trả đúng mẫu Áo thun màu Vani duy nhất trong context."),
    "conv-flt-0005-t1": score(*ALL_5_CONTEXT, "Giữ đúng ràng buộc Áo thun màu Vani và không bịa mẫu rẻ hơn."),

    # Ordinal follow-up.
    "conv-ord-0001-t0": score(*ALL_5, "Hai quần đều khớp chính xác tổ hợp Nâu / Trắng ngà."),
    "conv-ord-0001-t1": score(*ALL_5_CONTEXT, "Tham chiếu đúng sản phẩm thứ hai và mô tả đúng evidence."),
    "conv-ord-0002-t0": score(*ALL_5, "Hai đầm đều thuộc dải màu Xám than và đúng danh mục."),
    "conv-ord-0002-t1": score(*ALL_5_CONTEXT, "Tham chiếu đúng sản phẩm đầu tiên và mô tả đúng evidence."),
    "conv-ord-0003-t0": score(*ALL_5, "Ba sản phẩm đúng danh mục và màu Hồng."),
    "conv-ord-0003-t1": score(*ALL_5_CONTEXT, "Tham chiếu đúng sản phẩm thứ ba và mô tả đúng evidence."),
    "conv-ord-0004-t0": score(*ALL_5, "Chỉ trả mẫu khớp chính xác tổ hợp Màu cát / Đen; không chèn màu gần."),
    "conv-ord-0004-t1": score(
        2, 2, 2, 1, 1, 1, "NA", 2,
        "Lượt trước có danh sách nhưng chỉ có một mẫu. Cần nói không có mẫu thứ hai; câu trả lời lại khẳng định không có danh sách trước đó.",
    ),
    "conv-ord-0005-t0": score(*ALL_5, "Ba áo thun đều khớp chính xác màu Nâu chocolate."),
    "conv-ord-0005-t1": score(*ALL_5_CONTEXT, "Tham chiếu đúng sản phẩm đầu tiên và mô tả đúng evidence."),

    # Product comparison.
    "conv-cmp-0001-t0": score(*ALL_5, "Đủ hai sản phẩm, thuộc tính và kết luận giống/khác tường minh."),
    "conv-cmp-0002-t0": score(*ALL_5, "Đủ hai sản phẩm; nêu đúng điểm giống về danh mục và khác về màu/chất liệu."),
    "conv-cmp-0003-t0": score(*ALL_5, "So sánh đúng danh mục, màu và chất liệu; có kết luận giống/khác."),
    "conv-cmp-0004-t0": score(
        3, 3, 2, 1, 1, "NA", "NA", 2,
        "Chỉ truy hồi được đầm nâu thuốc lá nên không thực hiện so sánh; yêu cầu người dùng kiểm tra lại hai tên dù ground truth xác nhận cả hai.",
    ),
    "conv-cmp-0005-t0": score(*ALL_5, "Đủ hai sản phẩm và kết luận đúng các điểm khác về danh mục, màu, chất liệu."),
    "conv-cmp-0006-t0": score(*ALL_5, "Đủ hai sản phẩm; nêu đúng điểm giống về danh mục và khác về màu/chất liệu."),
    "conv-cmp-0007-t0": score(*ALL_5, "Đủ hai áo kiểu; kết luận giống/khác đúng evidence."),
    "conv-cmp-0008-t0": score(*ALL_5, "Đủ hai sản phẩm và kết luận khác nhau đúng về danh mục, màu, chất liệu."),

    # Product factual.
    "conv-fact-0019-t0": score(
        2, 2, 1, 1, "NA", "NA", "NA", 2,
        "Không trả lời giới tính Nữ dù reference và required evidence đã xác định; hỏi lại thông tin không cần làm rõ.",
    ),

    # Recommendations.
    "conv-rec-0001-t0": score(*ALL_5, "Ba Bodysuit đều đúng màu Đen, giới tính Nữ và đúng evidence."),
    "conv-rec-0002-t0": score(
        5, 5, 3, 4, 3, "NA", "NA", 3,
        "Hai mẫu đầu đúng màu Chàm; mẫu thứ ba màu Khaki vi phạm ràng buộc màu chính.",
    ),
    "conv-rec-0003-t0": score(
        1, 1, 2, 1, 1, "NA", "NA", 2,
        "Báo không tìm thấy, nhưng reference xác nhận có Quần dài màu nâu sọc mảnh có quai đai.",
    ),
    "conv-rec-0005-t0": score(*ALL_5, "Trả đúng mẫu Đỏ rượu vang, không bổ sung các mẫu Đỏ thường lệch sắc độ."),
    "conv-rec-0006-t0": score(*ALL_5, "Ba đầm đều đúng màu Đỏ, danh mục và giới tính."),
    "conv-rec-0007-t0": score(*ALL_5, "Ba đầm đều đúng màu Đen, danh mục và giới tính."),
    "conv-rec-0008-t0": score(*ALL_5, "Trả đúng mẫu Hồng pastel duy nhất thay vì chèn các sắc hồng khác."),
    "conv-rec-0010-t0": score(
        1, 1, 2, 1, 1, "NA", "NA", 2,
        "Báo không tìm thấy, nhưng reference xác nhận có áo hai dây màu Vàng ánh kim đính sequin.",
    ),
    "conv-rec-0013-t0": score(*ALL_5, "Ba áo kiểu đều đúng màu Trắng, danh mục và giới tính."),
    "conv-rec-0015-t0": score(*ALL_5, "Ba áo kiểu đều đúng màu Đen, danh mục và giới tính."),
    "conv-rec-0016-t0": score(*ALL_5, "Ba áo sơ mi đều khớp chính xác tổ hợp Hồng / Trắng."),
    "conv-rec-0018-t0": score(*ALL_5, "Trả đúng mẫu Nâu thuốc lá duy nhất, không chèn màu nâu gần."),
    "conv-rec-0019-t0": score(
        1, 1, 2, 1, 1, "NA", "NA", 2,
        "Báo không tìm thấy, nhưng reference xác nhận có Áo thun màu nâu đậm tay ngắn xẻ sau.",
    ),
    "conv-rec-0020-t0": score(*ALL_5, "Ba áo thun đều đúng màu Trắng, danh mục và giới tính."),
}


def is_accepted(row: dict[str, str]) -> bool:
    ratings = [row[field] for field in RATING_FIELDS if row[field] != "NA"]
    return all(int(value) >= 4 for value in ratings) and all(
        row[field] != "fail" for field in GATE_FIELDS
    )


def main() -> None:
    with PACKET.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames:
        raise RuntimeError("Reviewer A packet has no header")

    pending = {
        row["question_id"]
        for row in rows
        if row["review_notes"].startswith("CẦN CHẤM LẠI HẬU SỬA")
    }
    if pending != SCORES.keys():
        raise RuntimeError(
            f"Score mapping mismatch: missing={sorted(pending - SCORES.keys())}, "
            f"extra={sorted(SCORES.keys() - pending)}"
        )

    reviewed_rows: list[dict[str, str]] = []
    for row in rows:
        update = SCORES.get(row["question_id"])
        if update:
            row.update(update)
            reviewed_rows.append(row)

    with PACKET.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Kết quả chấm Reviewer A hậu sửa",
        "",
        "Reviewer A đã chấm 45 ca có đầu ra/context thay đổi. Điểm 1–5 và hard gate",
        "được áp dụng theo `evals/conversational_ai_validation/review/RUBRIC.md`.",
        "",
        "| ID | Câu hỏi | F | G | R | C | T | CR | RC | H | Hard gate | Kết quả | Nhận xét |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in sorted(reviewed_rows, key=lambda item: int(item["review_order"])):
        gates = ", ".join(
            f"{field.removeprefix('critical_')}={row[field]}"
            for field in GATE_FIELDS
            if row[field] != "NA"
        )
        note = row["review_notes"].removeprefix("[Reviewer A hậu sửa] ")
        question = row["question"].replace("|", "\\|").replace("\n", " ")
        note = note.replace("|", "\\|").replace("\n", " ")
        lines.append(
            "| "
            + " | ".join(
                [
                    row["question_id"],
                    question,
                    *(row[field] for field in RATING_FIELDS),
                    gates or "NA",
                    "Đạt" if is_accepted(row) else "Không đạt",
                    note,
                ]
            )
            + " |"
        )

    accepted = sum(is_accepted(row) for row in reviewed_rows)
    lines.extend(
        [
            "",
            f"Tổng hợp riêng 45 ca hậu sửa: **{accepted}/45 đạt**, "
            f"**{len(reviewed_rows) - accepted}/45 không đạt** theo Reviewer A.",
            "",
        ]
    )
    SUMMARY.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
