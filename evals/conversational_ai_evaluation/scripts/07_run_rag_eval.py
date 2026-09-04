from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
FIELDS = [
    "execution_id", "question_id", "session_id", "request_id", "turn_index", "category", "difficulty",
    "question", "http_status", "attempt_count", "latency_seconds", "answer",
    "retrieved_product_ids", "context_mode", "retrieved_context_json",
    "rewritten_query", "filters_json", "warnings_json", "route", "intent",
    "reference_resolution_source", "stage_latencies_json", "trace_schema_valid",
    "evaluation_trace_json", "error",
]


def main() -> int:
    args = parse_args()
    questions = read_csv(args.questions_csv)
    products = {row["product_id"]: row for row in read_csv(args.snapshot_csv)}
    rows = []
    for question in questions:
        if args.session_mode == "isolated_turns":
            session_id = f"{args.execution_id}:{question['question_id']}"
            turn_sequence = 1
            user_id = f"{args.execution_id}:{args.user_id}:{question['question_id']}"
        else:
            session_id = f"{args.execution_id}:{question['session_id']}"
            turn_sequence = int(question["turn_index"]) + 1
            user_id = f"{args.execution_id}:{args.user_id}"
        request_id = f"{args.execution_id}:{question['question_id']}"
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "request_id": request_id,
            "turn_sequence": turn_sequence,
            "message": question["question"],
            "locale": "vi-VN",
        }
        started = time.monotonic()
        response: dict = {}
        status = 0
        error = ""
        attempt_count = 0
        for attempt_count in range(1, args.retries + 2):
            response, status, error = post_json(
                args.endpoint, payload, args.timeout, args.bearer_token
            )
            if status == 200 or (status and status < 500):
                break
        latency = time.monotonic() - started
        trace = response.get("evaluation_trace")
        if not isinstance(trace, dict):
            trace = {}
        product_ids = trace_product_ids(trace) or response_product_ids(response)
        raw_context = trace.get("retrieved_context")
        if not isinstance(raw_context, list):
            raw_context = response.get("retrieved_context") or response.get("product_context")
        if isinstance(raw_context, list):
            context = raw_context
            context_mode = "full_context"
        else:
            context = [products[product_id] for product_id in product_ids if product_id in products]
            context_mode = "product_id_proxy"
        rows.append({
            "execution_id": args.execution_id,
            "question_id": question["question_id"],
            "session_id": session_id,
            "request_id": request_id,
            "turn_index": question["turn_index"], "category": question["category"],
            "difficulty": question["difficulty"], "question": question["question"],
            "http_status": status, "attempt_count": attempt_count,
            "latency_seconds": round(latency, 6),
            "answer": str(response.get("message") or ""),
            "retrieved_product_ids": "|".join(product_ids),
            "context_mode": context_mode,
            "retrieved_context_json": json.dumps(context, ensure_ascii=False, separators=(",", ":")),
            "rewritten_query": str(response.get("rewritten_query") or ""),
            "filters_json": json.dumps(response.get("filters"), ensure_ascii=False, separators=(",", ":")),
            "warnings_json": json.dumps(response.get("warnings"), ensure_ascii=False, separators=(",", ":")),
            "route": str(trace.get("route") or ""),
            "intent": str(trace.get("intent") or ""),
            "reference_resolution_source": str(trace.get("reference_resolution_source") or ""),
            "stage_latencies_json": json.dumps(trace.get("stage_latencies_ms") or {}, separators=(",", ":")),
            "trace_schema_valid": str(evaluation_trace_is_valid(trace)).lower(),
            "evaluation_trace_json": json.dumps(trace, ensure_ascii=False, separators=(",", ":")),
            "error": error,
        })
        write_csv(args.output_csv, rows, FIELDS)
        print(f"{question['question_id']} status={status} context={context_mode}")
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit_sha": git_commit_sha(),
        "catalog_snapshot": str(args.snapshot_csv),
        "qdrant_collection": os.getenv("QDRANT_TEXT_COLLECTION", "unknown"),
        "model_config": os.getenv("EVAL_MODEL_CONFIG", "runtime-environment"),
        "embedding_config": os.getenv("EVAL_EMBEDDING_CONFIG", "runtime-environment"),
        "reranker_config": os.getenv("EVAL_RERANKER_CONFIG", "runtime-environment"),
        "endpoint": args.endpoint,
        "seed": args.seed,
        "execution_id": args.execution_id,
        "evaluator_version": args.evaluator_version,
        "session_mode": args.session_mode,
        "context_modes": sorted({row["context_mode"] for row in rows}),
    }
    args.metadata_json.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_json.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    http_ok = all(int(row["http_status"]) == 200 for row in rows)
    trace_ok = all(row["trace_schema_valid"] == "true" for row in rows)
    return 0 if http_ok and (trace_ok or not args.require_evaluation_trace) else 1


def response_product_ids(response: dict) -> list[str]:
    raw = response.get("product_ids")
    if not isinstance(raw, list):
        raw = response.get("products") if isinstance(response.get("products"), list) else []
    result = []
    for item in raw:
        value = item.get("product_id") or item.get("id") if isinstance(item, dict) else item
        if value is not None:
            result.append(str(value))
    return list(dict.fromkeys(result))


def trace_product_ids(trace: dict) -> list[str]:
    candidates = trace.get("retrieved_candidates")
    if not isinstance(candidates, list):
        return []
    return response_product_ids({"product_ids": candidates})


def evaluation_trace_is_valid(trace: dict) -> bool:
    required = {
        "schema_version",
        "session_id_hash",
        "route",
        "rule_filters",
        "llm_filters",
        "effective_filters",
        "retrieved_candidates",
        "retrieved_context",
        "referenced_product_ids",
        "reference_resolution_source",
        "memory_sources",
        "warnings",
        "fallback_reasons",
        "stage_latencies_ms",
    }
    if not required.issubset(trace):
        return False
    session_hash = trace.get("session_id_hash")
    if not isinstance(session_hash, str) or len(session_hash) != 16:
        return False
    request_hash = trace.get("request_id_hash")
    if request_hash is not None and (
        not isinstance(request_hash, str) or len(request_hash) != 16
    ):
        return False
    return (
        isinstance(trace.get("retrieved_candidates"), list)
        and isinstance(trace.get("retrieved_context"), list)
        and isinstance(trace.get("stage_latencies_ms"), dict)
    )


def post_json(endpoint: str, payload: dict, timeout: float, token: str) -> tuple[dict, int, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode(), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode()), response.status, ""
    except HTTPError as error:
        return {}, error.code, error.read().decode(errors="replace")
    except URLError as error:
        return {}, 0, str(error.reason)
    except TimeoutError as error:
        return {}, 0, f"timeout: {error}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def git_commit_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=SCRIPT_DIR,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://localhost:8000/assistant/chat")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument(
        "--require-evaluation-trace",
        action="store_true",
        help="Fail the run unless every response contains a valid redacted eval trace.",
    )
    parser.add_argument("--user-id", default="rag-eval-user")
    parser.add_argument(
        "--session-mode",
        choices=("preserve_sessions", "isolated_turns"),
        default="preserve_sessions",
        help="Preserve multi-turn sessions or isolate every turn for no-memory baselines.",
    )
    parser.add_argument("--seed", type=int, default=252)
    parser.add_argument("--evaluator-version", default="rag-evaluator-v3")
    parser.add_argument(
        "--execution-id",
        default=datetime.now(timezone.utc).strftime("rag-%Y%m%dT%H%M%SZ"),
        help="Unique run instance prefix used to prevent checkpoint contamination.",
    )
    parser.add_argument("--bearer-token", default=os.getenv("EVAL_BEARER_TOKEN", ""))
    parser.add_argument("--questions-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "question_set.csv")
    parser.add_argument("--snapshot-csv", type=Path, default=SCRIPT_DIR.parent / "data" / "product_snapshot.csv")
    parser.add_argument("--output-csv", type=Path, default=SCRIPT_DIR.parent / "reports" / "rag_eval_responses.csv")
    parser.add_argument("--metadata-json", type=Path, default=SCRIPT_DIR.parent / "reports" / "rag_eval_run_metadata.json")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
