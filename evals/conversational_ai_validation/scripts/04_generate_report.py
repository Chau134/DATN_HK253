from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import SUITE_DIR, load_config, read_json, resolve


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "chưa có"
    if isinstance(value, float):
        return f"{value:.{digits}f}".replace(".", ",")
    return str(value)


def _tex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(char, char) for char in value)


def generate(config_path: Path | None = None) -> tuple[Path, Path]:
    config, base = load_config(config_path)
    automatic = read_json(resolve(base, config["source"]["metrics_summary_json"]))
    human_path = resolve(base, config["reports"]["human_validation_summary_json"])
    human = read_json(human_path) if human_path.exists() else None
    baseline_path = SUITE_DIR / "reports" / "baseline_comparison.json"
    baselines = read_json(baseline_path) if baseline_path.exists() else None
    critical_path = SUITE_DIR / "reports" / "critical_gate_summary.json"
    critical = read_json(critical_path) if critical_path.exists() else None

    metrics = automatic.get("metrics", {})
    category = automatic.get("breakdown", {}).get("category", {})
    difficulty = automatic.get("breakdown", {}).get("difficulty", {})
    rows = [
        ("Toàn bộ", automatic.get("question_count"), metrics.get("token_f1_relevancy")),
        ("Filter refinement", category.get("filter_refinement", {}).get("question_count"), category.get("filter_refinement", {}).get("token_f1_relevancy")),
        ("Follow-up ordinal", category.get("followup_ordinal", {}).get("question_count"), category.get("followup_ordinal", {}).get("token_f1_relevancy")),
        ("Nhóm khó", difficulty.get("hard", {}).get("question_count"), difficulty.get("hard", {}).get("token_f1_relevancy")),
    ]

    human_status = human.get("status") if human else "chưa tạo kết quả chấm"
    completed = human.get("completed_by_reviewer", {}) if human else {}
    agreement = human.get("overall_agreement", {}) if human else {}
    calibration = human.get("token_f1_calibration", {}) if human else {}

    markdown = [
        "# Kết quả kiểm định Conversational AI",
        "",
        "## Kết quả tự động hiện có",
        "",
        "| Nhóm | Số câu | Mức tương đồng token-F1 với câu trả lời tham chiếu |",
        "|---|---:|---:|",
    ]
    markdown.extend(f"| {name} | {count} | {_fmt(score)} |" for name, count, score in rows)
    markdown.extend([
        "",
        f"Rule-based grounding: {_fmt(metrics.get('rule_based_grounding_score'))}; "
        f"Context Precision: {_fmt(metrics.get('context_precision'))}; "
        f"Context Recall: {_fmt(metrics.get('context_recall'))}.",
        "",
        "Điểm trung bình toàn bộ vượt ngưỡng kỹ thuật tạm thời 0,70, nhưng các nhóm "
        "Filter refinement, Follow-up ordinal và nhóm khó đều thấp hơn ngưỡng. Vì vậy "
        "Token-F1 chỉ được dùng như chỉ số chẩn đoán, không phải kết luận về tính hữu ích.",
        "",
        "## Kiểm định bởi con người",
        "",
        f"Trạng thái: `{human_status}`. Reviewer A hoàn tất {completed.get('reviewer_a', 0)}/"
        f"{config['sample_size']} ca; Reviewer B hoàn tất {completed.get('reviewer_b', 0)}/"
        f"{config['sample_size']} ca.",
        "",
        f"Mức đồng thuận quyết định đạt/không đạt: {_fmt(agreement.get('percent_agreement'))}; "
        f"Cohen's kappa: {_fmt(agreement.get('cohen_kappa'))}.",
        "",
        f"Ngưỡng Token-F1 được đề xuất sau hiệu chỉnh: "
        f"{_fmt((calibration.get('recommended_threshold') or {}).get('threshold'))}.",
        (
            "Các con số đồng thuận và ngưỡng ở trên chỉ là AI pre-score minh họa, không đủ điều kiện "
            "đưa vào báo cáo cho đến khi hai reviewer con người xác nhận độc lập."
            if human_status in {"ai_prescore", "user_confirmed_prescore"} else ""
        ),
        "",
        "## Tiêu chí cứng",
        "",
        (
            f"Trạng thái: `{critical.get('status')}`; đã review "
            f"{critical.get('human_reviewed_count', 0)}/{critical.get('case_count', 12)} ca; "
            f"kết quả hard gate: {_fmt(critical.get('hard_gate_passed'))}."
            if critical else
            "Chưa chạy bộ 12 ca giá, tồn kho, sản phẩm không tồn tại và chính sách không có căn cứ."
        ),
        "",
        "## Đối chứng",
        "",
    ])
    if baselines:
        for variant in baselines.get("variants", []):
            markdown.append(f"- {variant['label']}: {variant['status']}.")
    else:
        markdown.append("Chưa chạy so sánh baseline.")
    markdown.extend([
        "",
        "Chỉ kết luận RAG làm giảm phát biểu không có căn cứ hoặc memory cải thiện khả năng "
        "giữ ràng buộc sau khi các baseline bắt buộc hoàn tất trên cùng tập câu hỏi và cấu hình.",
        "",
    ])

    if critical:
        critical_conclusion = (
            "Ng\u01b0\u1eddi review \u0111\u00e3 x\u00e1c nh\u1eadn \u0111\u1ee7 12/12 ca; hard gate \u0111\u1ea1t."
            if critical.get("hard_gate_passed")
            else (
                "K\u1ebft qu\u1ea3 t\u1ef1 \u0111\u1ed9ng l\u00e0 b\u1eb1ng ch\u1ee9ng chu\u1ea9n b\u1ecb review; "
                "hard gate ch\u1ec9 \u0111\u01b0\u1ee3c k\u1ebft lu\u1eadn sau khi con ng\u01b0\u1eddi x\u00e1c nh\u1eadn \u0111\u1ee7 12/12 ca."
            )
        )
        markdown.extend([
            "## K\u1ebft qu\u1ea3 t\u1ef1 \u0111\u1ed9ng cho 12 ca critical",
            "",
            (
                f"Automatic scorer \u0111\u1ea1t {critical.get('automatic_pass_count', 0)}/"
                f"{critical.get('case_count', 12)} ca. Human reviewer \u0111\u00e3 x\u00e1c nh\u1eadn "
                f"{critical.get('human_reviewed_count', 0)}/{critical.get('case_count', 12)} ca."
            ),
            "",
            critical_conclusion,
            "",
        ])

    if critical:
        automatic_passed = critical.get('automatic_pass_count', 0)
        case_count = critical.get('case_count', 12)
        markdown[-4] = (
            f'Automatic scorer đạt {automatic_passed}/{case_count} ca '
            'khi đối chiếu response, trace, context và evidence.'
        )
        markdown[-2] = (
            'Hard gate tự động đạt.'
            if critical.get('hard_gate_passed')
            else 'Hard gate tự động không đạt; xem danh sách ca lỗi.'
        )

    tex = [
        "% Generated by scripts/04_generate_report.py; verify before copying into the thesis.",
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Mức tương đồng token-F1 với câu trả lời tham chiếu theo nhóm}",
        r"\label{tab:conversational-token-f1-breakdown}",
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"\textbf{Nhóm} & \textbf{Số câu} & \textbf{Token-F1} \\",
        r"\midrule",
    ]
    for name, count, score in rows:
        tex.append(f"{_tex_escape(name)} & {count} & {_fmt(score)} \\\\")
    tex.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
        "Xét trên toàn bộ 80 câu hỏi, mức tương đồng token-F1 với câu trả lời tham chiếu "
        f"đạt {_fmt(metrics.get('token_f1_relevancy'))}. Tuy nhiên, kết quả theo nhóm cho thấy "
        f"Filter refinement đạt {_fmt(category.get('filter_refinement', {}).get('token_f1_relevancy'))}, "
        f"Follow-up ordinal đạt {_fmt(category.get('followup_ordinal', {}).get('token_f1_relevancy'))} "
        f"và nhóm câu khó đạt {_fmt(difficulty.get('hard', {}).get('token_f1_relevancy'))}. "
        "Do đó, giá trị trung bình toàn cục che khuất hạn chế ở các câu phụ thuộc ngữ cảnh "
        "và không được sử dụng riêng để kết luận chất lượng câu trả lời.",
        "",
    ])

    if critical:
        tex.extend([
            "K\u1ebft qu\u1ea3 ch\u1ea5m t\u1ef1 \u0111\u1ed9ng tr\u00ean 12 ca nh\u1ea1y c\u1ea3m \u0111\u1ea1t "
            f"{critical.get('automatic_pass_count', 0)}/{critical.get('case_count', 12)}. "
            "Tr\u1ea1ng th\u00e1i hard gate v\u1eabn ch\u1edd ng\u01b0\u1eddi \u0111\u00e1nh gi\u00e1 x\u00e1c nh\u1eadn.",
            "",
        ])

    md_path = SUITE_DIR / "reports" / "report_ready_summary.md"
    tex_path = SUITE_DIR / "reports" / "report_fragment.tex"
    md_path.write_text("\n".join(markdown), encoding="utf-8")
    tex_path.write_text("\n".join(tex), encoding="utf-8")
    return md_path, tex_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate report-ready Markdown and LaTeX.")
    parser.add_argument("--config", type=Path)
    return parser.parse_args()


def main() -> int:
    md_path, tex_path = generate(parse_args().config)
    print(md_path)
    print(tex_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
