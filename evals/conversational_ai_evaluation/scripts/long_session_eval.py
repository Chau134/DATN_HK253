from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from statistics import median
from time import monotonic
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROBE_NAMES = (
    "early_recall",
    "middle_recall",
    "recent_recall",
    "correction_supersedes_old_value",
    "reference_resolution",
    "cross_session_preference_recall",
    "session_isolation",
)


def build_primary_turns(case: dict[str, str]) -> list[dict[str, Any]]:
    budget = case["budget"]
    initial = case["initial_color"]
    corrected = case["corrected_color"]
    filler = [
        "Chào bạn, hôm nay thế nào?",
        "Cảm ơn nhé.",
        "Gợi ý cách phối hoodie với quần jean.",
        "Áo cotton nên giặt thế nào?",
        "Bạn có thể giúp gì khi mua thời trang?",
        "Mình đang cân nhắc thêm.",
    ]
    return [
        {
            "message": f"Mình thích hoodie nam màu {initial}, form rộng, ngân sách dưới {budget} nghìn.",
            "capture": "early",
        },
        {
            "message": "Tìm các mẫu đúng tiêu chí và gọi danh sách này là alpha.",
            "capture_anchor": "alpha",
        },
        *({"message": text} for text in filler),
        {
            "message": "Nhắc lại loại áo, màu ban đầu, form và ngân sách mình đã nói.",
            "probe": "early_recall",
            "must_include_all": ["hoodie", initial, "form rộng", budget],
        },
        {
            "message": "Mình ưu tiên chất liệu cotton và tránh màu đỏ.",
            "capture": "middle",
        },
        {
            "message": "Chất liệu ưu tiên và màu cần tránh của mình là gì?",
            "probe": "middle_recall",
            "must_include_all": ["cotton", "đỏ"],
        },
        {
            "message": f"Không phải màu {initial} nữa, đổi sang màu {corrected}.",
            "capture": "correction",
        },
        {
            "message": "Tìm lại theo màu mới và gọi danh sách này là beta.",
            "capture_anchor": "beta",
        },
        {
            "message": "Cái thứ 1 vừa rồi thì sao?",
            "probe": "reference_resolution",
            "expected_anchor": "beta",
            "expected_ordinal": 1,
        },
        {
            "message": "Cái thứ 1 trong danh sách alpha thì sao?",
            "probe": "reference_resolution",
            "expected_anchor": "alpha",
            "expected_ordinal": 1,
        },
        {"message": "Mình sẽ xem thêm rồi quyết định."},
        {"message": "Hoodie form rộng phối giày gì?"},
        {"message": "Cảm ơn, tư vấn rất hữu ích."},
        {
            "message": "Mình mặc size L, hãy ghi nhớ.",
            "capture": "recent",
        },
        {
            "message": (
                "Tổng hợp tiêu chí hiện tại: loại áo, màu mới, màu đã bỏ, ngân sách, "
                "chất liệu, màu tránh và size."
            ),
            "probes": [
                {
                    "name": "early_recall",
                    "must_include_all": ["hoodie", budget],
                },
                {
                    "name": "middle_recall",
                    "must_include_all": ["cotton", "đỏ"],
                },
                {
                    "name": "recent_recall",
                    "must_include_all": ["size l"],
                },
                {
                    "name": "correction_supersedes_old_value",
                    "expected_current_value": corrected,
                    "superseded_value": initial,
                },
            ],
        },
    ]


def run(config: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_id = deterministic_run_id(config)
    execution_id = args.execution_id
    rows: list[dict[str, Any]] = []
    completed_sessions = 0
    session_stats: list[dict[str, Any]] = []

    for session_case in config["sessions"]:
        case_id = session_case["case_id"]
        primary_user = f"{execution_id}:{run_id}:{case_id}:user"
        primary_session = f"{execution_id}:{run_id}:{case_id}:session"
        anchors: dict[str, list[str]] = {}
        primary_rows: list[dict[str, Any]] = []
        turns = build_primary_turns(session_case)
        for turn_index, turn in enumerate(turns, start=1):
            row = execute_turn(
                args,
                case_id=case_id,
                user_id=primary_user,
                session_id=primary_session,
                turn_index=turn_index,
                turn=turn,
                anchors=anchors,
            )
            rows.append(row)
            primary_rows.append(row)
            print(
                f"{case_id} turn={turn_index}/{len(turns)} status={row['http_status']} "
                f"nonempty={row['nonempty']}",
                flush=True,
            )
            if turn.get("capture_anchor"):
                anchors[str(turn["capture_anchor"])] = list(row["product_ids"])

        completed = len(primary_rows) == len(turns) and all(row["http_ok"] for row in primary_rows)
        completed_sessions += int(completed)
        session_stats.append(
            {
                "case_id": case_id,
                "turn_count": len(primary_rows),
                "completed": completed,
                "expected_compaction": len(primary_rows) * 2 > 12,
                "http_success_count": sum(int(row["http_ok"]) for row in primary_rows),
                "nonempty_count": sum(int(row["nonempty"]) for row in primary_rows),
            }
        )

        cross_turn = {
            "message": "Ở phiên mới, nhắc lại gu hoodie, màu hiện tại, chất liệu, size và ngân sách của mình.",
            "probe": "cross_session_preference_recall",
            "must_include_all": [
                "hoodie",
                session_case["corrected_color"],
                "cotton",
                "size l",
                session_case["budget"],
            ],
        }
        rows.append(
            execute_turn(
                args,
                case_id=case_id,
                user_id=primary_user,
                session_id=f"{primary_session}:new",
                turn_index=1,
                turn=cross_turn,
                anchors={},
            )
        )
        isolation_turn = {
            "message": "Gu, màu, chất liệu, size và ngân sách trước đây của mình là gì?",
            "probe": "session_isolation",
            "must_include_any": [
                "chưa có",
                "chưa ghi nhớ",
                "chưa biết",
                "bạn chưa",
                "không thể truy cập",
                "không có lịch sử",
                "không có thông tin",
            ],
            "must_not_include": [
                session_case["budget"],
                "cotton",
                "size l",
                session_case["corrected_color"],
            ],
        }
        rows.append(
            execute_turn(
                args,
                case_id=case_id,
                user_id=f"{primary_user}:other",
                session_id=primary_session,
                turn_index=1,
                turn=isolation_turn,
                anchors={},
            )
        )
        rows.append(
            execute_turn(
                args,
                case_id=case_id,
                user_id=f"{primary_user}:brand-new",
                session_id=f"{primary_session}:brand-new",
                turn_index=1,
                turn={**isolation_turn, "probe": "false_memory"},
                anchors={},
            )
        )

    summary = summarize(
        rows,
        session_count=len(config["sessions"]),
        completed_sessions=completed_sessions,
        thresholds=config["thresholds"],
    )
    summary["run_id"] = run_id
    summary["execution_id"] = execution_id
    summary["config_version"] = config["version"]
    summary["seed"] = config["seed"]
    summary["session_statistics"] = session_stats
    return summary, rows


def execute_turn(
    args: argparse.Namespace,
    *,
    case_id: str,
    user_id: str,
    session_id: str,
    turn_index: int,
    turn: dict[str, Any],
    anchors: dict[str, list[str]],
) -> dict[str, Any]:
    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "request_id": f"{case_id}:{hash_id(user_id)}:{hash_id(session_id)}:{turn_index}",
        "turn_sequence": turn_index,
        "message": turn["message"],
        "locale": "vi-VN",
    }
    started = monotonic()
    response: dict[str, Any] = {}
    status = 0
    error: str | None = None
    attempt_count = 0
    for attempt_count in range(1, args.retries + 2):
        response, status, error = post_json(
            args.endpoint, payload, args.timeout, args.bearer_token
        )
        if status == 200 or (status and status < 500):
            break
    latency = monotonic() - started
    message = str(response.get("message") or "").strip()
    product_ids = response_product_ids(response)
    normalized = normalize(message)
    probe_results: list[dict[str, Any]] = []
    probe_specs = list(turn.get("probes", []))
    if turn.get("probe"):
        probe_specs.append({"name": turn["probe"], **turn})
    for probe in probe_specs:
        checks: dict[str, bool] = {}
        required = [normalize(str(value)) for value in probe.get("must_include_all", [])]
        if required:
            checks["must_include_all"] = all(value in normalized for value in required)
        required_any = [normalize(str(value)) for value in probe.get("must_include_any", [])]
        if required_any:
            checks["must_include_any"] = any(value in normalized for value in required_any)
        forbidden = [normalize(str(value)) for value in probe.get("must_not_include", [])]
        if forbidden:
            checks["must_not_include"] = not any(value in normalized for value in forbidden)
        anchor_name = probe.get("expected_anchor")
        if anchor_name:
            ordinal = int(probe.get("expected_ordinal", 1))
            expected = anchors.get(str(anchor_name), [])
            checks["expected_product_reference"] = (
                len(expected) >= ordinal and expected[ordinal - 1] in product_ids
            )
        if probe.get("expected_current_value") and probe.get("superseded_value"):
            checks["correction_supersedes"] = correction_supersedes_old_value(
                message,
                current_value=str(probe["expected_current_value"]),
                old_value=str(probe["superseded_value"]),
            )
        probe_results.append(
            {
                "name": probe["name"],
                "passed": bool(checks) and all(checks.values()),
                "checks": checks,
            }
        )

    raw_warnings = response.get("warnings")
    warnings = [str(value) for value in raw_warnings] if isinstance(raw_warnings, list) else []
    unsupported_availability = is_unsupported_availability_claim(
        message,
        product_ids=product_ids,
        warnings=warnings,
    )
    return {
        "case_id": case_id,
        "user_id": hash_id(user_id),
        "session_id": hash_id(session_id),
        "turn_index": turn_index,
        "request_id": hash_id(str(payload["request_id"])),
        "user_message": redact(str(turn["message"])),
        "assistant_message": redact(message),
        "product_ids": product_ids,
        "warnings": warnings,
        "http_status": status,
        "attempt_count": attempt_count,
        "http_ok": status == 200 and error is None,
        "nonempty": bool(message),
        "latency_seconds": round(latency, 6),
        "probe_results": probe_results,
        "unsupported_availability_claim": unsupported_availability,
        "error": redact(error or ""),
    }


def summarize(
    rows: list[dict[str, Any]],
    *,
    session_count: int,
    completed_sessions: int,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    probes: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        for probe in row["probe_results"]:
            probes[str(probe["name"])].append(bool(probe["passed"]))
    latencies = [float(row["latency_seconds"]) for row in rows]
    primary = [row for row in rows if int(row["turn_index"]) > 1]
    early_latencies = [float(row["latency_seconds"]) for row in primary if int(row["turn_index"]) <= 5]
    late_latencies = [float(row["latency_seconds"]) for row in primary if int(row["turn_index"]) >= 16]
    false_memory = probes.get("false_memory", [])
    metrics: dict[str, float] = {
        "completed_session_rate": ratio(completed_sessions, session_count),
        "http_success_rate": ratio(sum(int(row["http_ok"]) for row in rows), len(rows)),
        "nonempty_response_rate": ratio(sum(int(row["nonempty"]) for row in rows), len(rows)),
        **{
            name: ratio(sum(results), len(results))
            for name in PROBE_NAMES
            if (results := probes.get(name, []))
        },
        "false_memory_rate": ratio(len(false_memory) - sum(false_memory), len(false_memory)),
        "unsupported_availability_claim_rate": ratio(
            sum(int(row["unsupported_availability_claim"]) for row in rows),
            len(rows),
        ),
        "p95_latency_seconds": percentile(latencies, 0.95),
        "late_to_early_latency_ratio": round(
            median(late_latencies) / max(median(early_latencies), 0.001),
            4,
        )
        if early_latencies and late_latencies
        else 0.0,
    }
    checks: dict[str, bool] = {}
    for name, threshold in thresholds.items():
        metric = name.removeprefix("min_").removeprefix("max_")
        if name.startswith("min_"):
            checks[name] = metrics.get(metric, 0.0) >= float(threshold)
        elif name.startswith("max_"):
            checks[name] = metrics.get(metric, math.inf) <= float(threshold)
        else:
            raise ValueError(f"Unsupported threshold: {name}")
    return {
        "session_count": session_count,
        "completed_sessions": completed_sessions,
        "total_requests": len(rows),
        "metrics": metrics,
        "probe_counts": {
            name: {"passed": sum(results), "total": len(results)}
            for name, results in sorted(probes.items())
        },
        "threshold_checks": checks,
        "acceptance_passed": all(checks.values()),
    }


def write_reports(
    report_root: Path,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
) -> Path:
    output_dir = report_root / str(summary["run_id"])
    if summary.get("execution_id"):
        output_dir = output_dir / str(summary["execution_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "transcript.redacted.jsonl").open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    probes = [
        {
            "case_id": row["case_id"],
            "session_id": row["session_id"],
            "turn_index": row["turn_index"],
            **probe,
        }
        for row in rows
        for probe in row["probe_results"]
    ]
    with (output_dir / "probe_results.jsonl").open("w", encoding="utf-8") as output:
        for probe in probes:
            output.write(json.dumps(probe, ensure_ascii=False) + "\n")
    (output_dir / "checkpoint_statistics.json").write_text(
        json.dumps(
            {
                "run_id": summary["run_id"],
                "sessions": summary["session_statistics"],
                "note": "Counts are black-box checkpoint/compaction coverage statistics; no message content is stored.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_dir


def post_json(
    endpoint: str,
    payload: dict[str, Any],
    timeout: float,
    bearer_token: str | None,
) -> tuple[dict[str, Any], int, str | None]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), response.status, None
    except HTTPError as error:
        return {}, error.code, error.read().decode("utf-8", errors="replace")
    except URLError as error:
        return {}, 0, str(error.reason)
    except TimeoutError as error:
        return {}, 0, f"timeout: {error}"


def response_product_ids(response: dict[str, Any]) -> list[str]:
    products = response.get("product_ids")
    if not isinstance(products, list):
        products = response.get("products") if isinstance(response.get("products"), list) else []
    values: list[str] = []
    for item in products:
        if isinstance(item, dict):
            product_id = item.get("product_id") or item.get("id")
        else:
            product_id = item
        if product_id is not None:
            values.append(str(product_id))
    return values


def has_unsupported_availability_claim(message: str) -> bool:
    normalized = normalize(message)
    patterns = (r"\bcon hang\b", r"\bsan hang\b", r"\bin stock\b", r"\bavailable\b")
    for pattern in patterns:
        for match in re.finditer(pattern, normalized):
            prefix = normalized[max(0, match.start() - 35) : match.start()]
            if not any(
                negation in prefix
                for negation in (
                    "khong the xac nhan",
                    "chua the xac nhan",
                    "khong co du lieu",
                    "khong biet",
                    "cannot confirm",
                    "no evidence",
                )
            ):
                return True
    return False


def is_unsupported_availability_claim(
    message: str,
    *,
    product_ids: list[str],
    warnings: list[str],
) -> bool:
    if not has_unsupported_availability_claim(message):
        return False
    return not product_ids or "spring_boot_unavailable" in warnings


def correction_supersedes_old_value(
    message: str,
    *,
    current_value: str,
    old_value: str,
) -> bool:
    normalized = normalize(message)
    current = normalize(current_value)
    old = normalize(old_value)
    old_is_superseded = any(
        phrase in normalized
        for phrase in (
            f"da bo mau {old}",
            f"khong con mau {old}",
            f"doi tu mau {old}",
            f"thay mau {old}",
        )
    )
    current_is_active = any(
        phrase in normalized
        for phrase in (
            f"mau moi la {current}",
            f"mau hien tai la {current}",
            f"doi sang mau {current}",
            f"mau {current} da bo mau {old}",
            f"mau {current} (da bo mau {old}",
        )
    )
    return old_is_superseded and current_is_active


def deterministic_run_id(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"longmem-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12]}"


def hash_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def redact(value: str) -> str:
    value = re.sub(r"(?i)\b(bearer|token|api[_ -]?key)\s*[:=]\s*\S+", r"\1=[REDACTED]", value)
    value = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", value)
    value = re.sub(r"(?<!\d)(?:\+?84|0)\d{9,10}(?!\d)", "[REDACTED_PHONE]", value)
    return value


def normalize(value: str) -> str:
    text = value.strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text)


def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * quantile) - 1)
    return round(ordered[index], 6)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic long-session memory acceptance evals.")
    parser.add_argument("--endpoint", default="http://localhost:8080/api/assistant/chat")
    parser.add_argument(
        "--config",
        type=Path,
        default=SCRIPT_DIR.parent / "configs" / "long_session_cases.json",
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=SCRIPT_DIR.parent / "reports" / "long_session",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument(
        "--execution-id",
        default=datetime.now(timezone.utc).strftime("long-%Y%m%dT%H%M%SZ"),
        help="Unique run instance prefix used to prevent checkpoint contamination.",
    )
    parser.add_argument("--bearer-token", default=os.getenv("EVAL_BEARER_TOKEN"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    summary, rows = run(config, args)
    output_dir = write_reports(args.report_root, summary, rows)
    print(json.dumps({"output_dir": str(output_dir), **summary}, ensure_ascii=False, indent=2))
    return 0 if summary["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
