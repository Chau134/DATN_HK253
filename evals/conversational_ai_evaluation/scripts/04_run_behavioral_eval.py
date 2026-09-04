from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> int:
    args = parse_args()
    config = json.loads(args.cases.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    session_sequences: dict[str, int] = defaultdict(int)

    for case in config.get("cases", []):
        for turn_index, turn in enumerate(case.get("turns", []), start=1):
            session_id = f"{args.execution_id}:{turn['session_id']}"
            session_sequences[session_id] += 1
            turn_sequence = session_sequences[session_id]
            payload = {
                "session_id": session_id,
                "user_id": f"{args.execution_id}:{case['user_id']}",
                "request_id": f"{args.execution_id}:{case['case_id']}:{turn_index}",
                "turn_sequence": turn_sequence,
                "message": turn["message"],
                "locale": "vi-VN",
            }
            response: dict[str, object] = {}
            error: str | None = None
            attempt_count = 0
            for attempt_count in range(1, args.retries + 2):
                response, error = post_json(
                    args.endpoint, payload, args.timeout, args.bearer_token
                )
                status = int(response.get("_http_status", 0))
                if status == 200 or (status and status < 500):
                    break
            row = score_turn(case["case_id"], turn_index, turn, response, error)
            row["execution_id"] = args.execution_id
            row["effective_session_id"] = session_id
            row["turn_sequence"] = turn_sequence
            row["attempt_count"] = attempt_count
            rows.append(row)
            write_csv(args.results_csv, rows)
            print(f"{row['case_id']} turn={turn_index} passed={row['passed']} status={row['http_status']}")

    write_csv(args.results_csv, rows)
    summary = summarize(rows, config.get("thresholds", {}))
    summary["execution_id"] = args.execution_id
    summary["endpoint"] = args.endpoint
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed_turns"] == 0 and summary["thresholds_passed"] else 1


def post_json(
    endpoint: str,
    payload: dict[str, object],
    timeout: float,
    bearer_token: str | None,
) -> tuple[dict[str, object], str | None]:
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
            body = json.loads(response.read().decode("utf-8"))
            body["_http_status"] = response.status
            return body, None
    except HTTPError as error:
        return {"_http_status": error.code}, error.read().decode("utf-8", errors="replace")
    except URLError as error:
        return {"_http_status": 0}, str(error.reason)
    except TimeoutError as error:
        return {"_http_status": 0}, f"timeout: {error}"


def score_turn(
    case_id: str,
    turn_index: int,
    turn: dict[str, object],
    response: dict[str, object],
    error: str | None,
) -> dict[str, object]:
    message = str(response.get("message") or "").strip()
    products = response.get("products")
    if not isinstance(products, list):
        products = response.get("product_ids") if isinstance(response.get("product_ids"), list) else []
    normalized = normalize(message)
    checks: list[tuple[str, bool]] = [("http_ok", response.get("_http_status") == 200 and error is None)]

    if turn.get("expect_nonempty_response"):
        checks.append(("nonempty_response", bool(message)))
    if turn.get("expect_no_products"):
        checks.append(("no_product_retrieval", len(products) == 0))

    must_include_any = [normalize(str(value)) for value in turn.get("must_include_any", [])]
    if must_include_any:
        checks.append(("required_concept", any(value in normalized for value in must_include_any)))
    must_not_include = [normalize(str(value)) for value in turn.get("must_not_include", [])]
    if must_not_include:
        checks.append(("forbidden_phrase_absent", not any(value in normalized for value in must_not_include)))

    failed_checks = [name for name, passed in checks if not passed]
    return {
        "case_id": case_id,
        "turn_index": turn_index,
        "category": turn.get("category", "unknown"),
        "session_id": turn.get("session_id", ""),
        "user_message": turn.get("message", ""),
        "assistant_message": message,
        "normalized_response": normalized,
        "product_count": len(products),
        "http_status": response.get("_http_status", 0),
        "passed": not failed_checks,
        "failed_checks": "|".join(failed_checks),
        "error": error or "",
    }


def summarize(rows: list[dict[str, object]], thresholds: dict[str, object]) -> dict[str, object]:
    total = len(rows)
    failed = sum(1 for row in rows if not row["passed"])
    small_talk = [row for row in rows if row["category"] in {"small_talk", "capability"}]
    preference = [row for row in rows if row["category"] == "preference_recall"]
    repeated = _exact_repeat_count(small_talk)
    summary: dict[str, object] = {
        "total_turns": total,
        "passed_turns": total - failed,
        "failed_turns": failed,
        "turn_pass_rate": ratio(total - failed, total),
        "small_talk_no_retrieval_rate": ratio(
            sum(1 for row in small_talk if int(row["product_count"]) == 0),
            len(small_talk),
        ),
        "preference_recall_rate": ratio(
            sum(1 for row in preference if row["passed"]),
            len(preference),
        ),
        "exact_small_talk_response_repeat_rate": ratio(repeated, len(small_talk)),
    }
    threshold_checks = evaluate_thresholds(summary, thresholds)
    summary["threshold_checks"] = threshold_checks
    summary["thresholds_passed"] = all(threshold_checks.values())
    return summary


def evaluate_thresholds(
    summary: dict[str, object],
    thresholds: dict[str, object],
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for threshold_name, raw_threshold in thresholds.items():
        if threshold_name.startswith("min_"):
            metric_name = threshold_name.removeprefix("min_")
            value = summary.get(metric_name)
            checks[threshold_name] = value is not None and float(value) >= float(raw_threshold)
        elif threshold_name.startswith("max_"):
            metric_name = threshold_name.removeprefix("max_")
            value = summary.get(metric_name)
            checks[threshold_name] = value is not None and float(value) <= float(raw_threshold)
        else:
            raise ValueError(f"Unsupported threshold name: {threshold_name}")
    return checks


def _exact_repeat_count(rows: list[dict[str, object]]) -> int:
    seen: set[str] = set()
    repeated = 0
    for row in rows:
        response = str(row["normalized_response"])
        if response and response in seen:
            repeated += 1
        seen.add(response)
    return repeated


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def normalize(value: str) -> str:
    text = value.strip().lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run behavioral chat evals through the assistant API.")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8080/api/assistant/chat",
        help="Spring Boot assistant endpoint (or direct FastAPI /assistant/chat).",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=SCRIPT_DIR.parent / "configs" / "behavioral_cases.json",
    )
    parser.add_argument(
        "--results-csv",
        type=Path,
        default=SCRIPT_DIR.parent / "reports" / "behavioral_results.csv",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=SCRIPT_DIR.parent / "reports" / "behavioral_summary.json",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument(
        "--execution-id",
        default=datetime.now(timezone.utc).strftime("behavior-%Y%m%dT%H%M%SZ"),
        help="Unique run instance prefix used to prevent checkpoint contamination.",
    )
    parser.add_argument("--bearer-token", default=os.getenv("EVAL_BEARER_TOKEN"))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
