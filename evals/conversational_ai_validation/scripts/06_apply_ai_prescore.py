from __future__ import annotations

import csv
from pathlib import Path

from common import SUITE_DIR, read_csv, write_csv


RATING_FIELDS = (
    "factual_correctness", "groundedness", "answer_relevancy", "completeness",
    "task_success", "context_retention", "refusal_correctness", "helpfulness",
)


def score(*values: str, note: str, gates: dict[str, str] | None = None) -> dict[str, str]:
    assert len(values) == len(RATING_FIELDS)
    result = dict(zip(RATING_FIELDS, values))
    result.update(gates or {})
    result["review_notes"] = f"AI pre-score — cần human review: {note}"
    return result


GOOD_PRODUCT = ("5", "5", "5", "5", "5", "NA", "NA", "5")
GOOD_FACT = ("5", "5", "5", "5", "NA", "NA", "NA", "5")
COMPARISON_PARTIAL = ("5", "5", "5", "3", "4", "NA", "NA", "4")

SCORES = {
    "conv-flt-0001-t0": score(*GOOD_PRODUCT, note="Ba sản phẩm đều đúng danh mục Quần dài, màu Nâu melange và dữ kiện khớp context.", gates={"critical_product_exists": "pass"}),
    "conv-flt-0002-t1": score("5", "5", "2", "2", "2", "2", "NA", "2", note="Mất ràng buộc Đỏ/Trắng ở hai lựa chọn; giá thấp nhất mới 579.000 VND không rẻ hơn mức thấp nhất 539.000 VND của lượt trước.", gates={"critical_price": "fail", "critical_product_exists": "pass"}),
    "conv-flt-0003-t0": score(*GOOD_PRODUCT, note="Ba sản phẩm đều đúng danh mục và màu Nâu; các thuộc tính khớp context.", gates={"critical_product_exists": "pass"}),
    "conv-flt-0004-t0": score(*GOOD_PRODUCT, note="Ba sản phẩm đều đúng danh mục Áo kiểu và màu Xanh dương nhạt.", gates={"critical_product_exists": "pass"}),
    "conv-flt-0004-t1": score("5", "5", "2", "2", "2", "2", "NA", "2", note="Đổi đúng sang màu Đen nhưng làm mất danh mục Áo kiểu; kết quả gồm Áo thun và cả Quần sarouel.", gates={"critical_product_exists": "pass"}),

    "conv-ord-0001-t1": score("5", "5", "5", "5", "5", "5", "NA", "5", note="Phân giải đúng sản phẩm thứ hai id 1875 và mô tả đúng context.", gates={"critical_product_exists": "pass"}),
    "conv-ord-0002-t0": score("5", "5", "3", "3", "3", "NA", "NA", "3", note="Chỉ một lựa chọn đúng chính xác Xám than; Xám than đậm gần đúng và Xám tro không giữ đúng sắc độ yêu cầu.", gates={"critical_product_exists": "pass"}),
    "conv-ord-0003-t0": score(*GOOD_PRODUCT, note="Ba lựa chọn đều đúng danh mục, màu Hồng và giới tính.", gates={"critical_product_exists": "pass"}),
    "conv-ord-0004-t0": score("5", "5", "3", "3", "3", "NA", "NA", "3", note="Chỉ lựa chọn đầu thỏa đúng màu kết hợp Màu cát/Đen; hai lựa chọn còn lại chỉ màu Đen.", gates={"critical_product_exists": "pass"}),
    "conv-ord-0005-t1": score("5", "5", "5", "5", "5", "5", "NA", "5", note="Phân giải đúng mẫu đầu tiên id 762 và mọi thuộc tính khớp context.", gates={"critical_product_exists": "pass"}),

    "conv-cmp-0004-t0": score(*COMPARISON_PARTIAL, note="Dữ kiện hai sản phẩm đúng nhưng chưa tổng hợp rõ điểm giống và khác như reference yêu cầu.", gates={"critical_product_exists": "pass"}),
    "conv-cmp-0006-t0": score(*COMPARISON_PARTIAL, note="Dữ kiện hai sản phẩm đúng nhưng chưa tổng hợp rõ điểm giống và khác như reference yêu cầu.", gates={"critical_product_exists": "pass"}),
    "conv-cmp-0007-t0": score(*COMPARISON_PARTIAL, note="Dữ kiện hai sản phẩm đúng nhưng chưa tổng hợp rõ điểm giống và khác như reference yêu cầu.", gates={"critical_product_exists": "pass"}),
    "conv-cmp-0009-t0": score(*COMPARISON_PARTIAL, note="Dữ kiện hai sản phẩm đúng nhưng chưa tổng hợp rõ điểm giống và khác như reference yêu cầu.", gates={"critical_product_exists": "pass"}),
    "conv-cmp-0010-t0": score(*COMPARISON_PARTIAL, note="Dữ kiện hai sản phẩm đúng nhưng chưa tổng hợp rõ điểm giống và khác như reference yêu cầu.", gates={"critical_product_exists": "pass"}),

    "conv-fact-0001-t0": score(*GOOD_FACT, note="Màu Đen khớp chính xác evidence và context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0002-t0": score(*GOOD_FACT, note="Thành phần chất liệu khớp chính xác context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0006-t0": score(*GOOD_FACT, note="Thành phần chất liệu khớp chính xác context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0007-t0": score(*GOOD_FACT, note="Giới tính Nữ khớp chính xác evidence và context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0008-t0": score(*GOOD_FACT, note="Danh mục Váy & Đầm khớp chính xác context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0010-t0": score(*GOOD_FACT, note="Chất liệu 100% Viscose khớp chính xác context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0013-t0": score(*GOOD_FACT, note="Màu Cam cháy khớp chính xác evidence và context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0015-t0": score(*GOOD_FACT, note="Giới tính Nữ khớp chính xác evidence và context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0016-t0": score(*GOOD_FACT, note="Danh mục Áo sơ mi khớp chính xác context.", gates={"critical_product_exists": "pass"}),
    "conv-fact-0020-t0": score(*GOOD_FACT, note="Danh mục Áo thun khớp chính xác context.", gates={"critical_product_exists": "pass"}),

    "conv-rec-0002-t0": score("5", "5", "3", "3", "3", "NA", "NA", "3", note="Hai sản phẩm đúng màu Chàm, nhưng lựa chọn thứ ba màu Khaki vi phạm ràng buộc chính.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0004-t0": score("5", "5", "3", "3", "3", "NA", "NA", "3", note="Có kết quả thuộc Quần legging trong khi yêu cầu Quần dài; câu trả lời cũng đổi nhãn danh mục ở phần mở đầu.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0005-t0": score("5", "5", "2", "2", "2", "NA", "NA", "2", note="Chỉ một trong ba lựa chọn đúng sắc độ Đỏ rượu vang; hai lựa chọn còn lại chỉ màu Đỏ.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0006-t0": score(*GOOD_PRODUCT, note="Ba lựa chọn đều đúng Váy & Đầm màu Đỏ cho Nữ.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0007-t0": score(*GOOD_PRODUCT, note="Ba lựa chọn đều đúng Váy & Đầm màu Đen cho Nữ.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0011-t0": score("5", "5", "2", "2", "2", "NA", "NA", "2", note="Yêu cầu Nâu chocolate nhưng cả ba lựa chọn chỉ được gắn màu Nâu.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0016-t0": score(*GOOD_PRODUCT, note="Các lựa chọn đều thuộc Áo sơ mi, có màu Hồng hoặc Trắng và đúng giới tính; chỗ thiếu chất liệu được nói rõ thay vì bịa.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0018-t0": score("5", "5", "2", "2", "2", "NA", "NA", "2", note="Chỉ lựa chọn đầu đúng Nâu thuốc lá; hai lựa chọn còn lại chỉ màu Nâu.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0019-t0": score("5", "5", "2", "2", "2", "NA", "NA", "2", note="Không lựa chọn nào được context xác nhận là Nâu đậm; cả ba chỉ màu Nâu.", gates={"critical_product_exists": "pass"}),
    "conv-rec-0020-t0": score(*GOOD_PRODUCT, note="Ba lựa chọn đều đúng Áo thun màu Trắng cho Nữ.", gates={"critical_product_exists": "pass"}),

    "conv-shop-0001-t0": score("5", "5", "5", "5", "NA", "NA", "NA", "5", note="Tên và địa chỉ shop khớp hoàn toàn evidence.", gates={"critical_policy": "pass"}),
    "conv-shop-0003-t0": score("3", "3", "5", "5", "NA", "NA", "NA", "4", note="Các mốc giao hàng chính đúng, nhưng câu thêm 'dịp cao điểm tối đa 48 giờ' không có trong evidence.", gates={"critical_policy": "fail"}),
    "conv-shop-0005-t0": score("4", "4", "5", "5", "NA", "NA", "NA", "5", note="Các phương thức thanh toán đúng; câu thêm việc thông tin chuyển khoản được cung cấp sau đặt hàng không có trong evidence.", gates={"critical_policy": "fail"}),
    "conv-shop-0007-t0": score("3", "3", "5", "5", "NA", "NA", "NA", "4", note="Kết luận đơn dưới 100k không freeship và hai ngưỡng miễn phí đúng; các mức phí 20k/30k/40–60k không có trong evidence của packet.", gates={"critical_price": "fail", "critical_policy": "fail"}),

    "conv-una-v2-0001-t0": score("NA", "5", "5", "5", "NA", "NA", "4", "4", note="Từ chối xác nhận công dụng đúng khi thiếu dữ liệu; còn thiếu bước tiếp theo như liên hệ CSKH.", gates={"critical_clarification_or_refusal": "pass"}),
}


def apply_scores(path: Path) -> None:
    rows = read_csv(path)
    unknown = sorted({row["question_id"] for row in rows} - set(SCORES))
    missing = sorted(set(SCORES) - {row["question_id"] for row in rows})
    if unknown or missing:
        raise ValueError(f"Score map mismatch: unknown={unknown}; missing={missing}")
    for row in rows:
        row.update(SCORES[row["question_id"]])
    fields = list(rows[0].keys())
    write_csv(path, rows, fields)


def main() -> int:
    for name in ("reviewer_a.csv", "reviewer_b.csv"):
        apply_scores(SUITE_DIR / "review" / name)
        print(f"Updated {name} with AI pre-score for {len(SCORES)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
