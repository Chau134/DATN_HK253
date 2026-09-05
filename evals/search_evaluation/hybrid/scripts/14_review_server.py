from __future__ import annotations

import argparse
import csv
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
REVIEW_DIR = ROOT / "reports" / "review"
CSV_PATH = REVIEW_DIR / "hybrid_candidate_review.csv"
EDITABLE = {
    "hard_constraints_satisfied",
    "visual_similarity",
    "relevance_grade",
    "confidence",
    "review_status",
    "reviewer_notes",
}
LOCK = threading.Lock()


def read_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(rows: list[dict[str, str]]) -> None:
    temporary = CSV_PATH.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, CSV_PATH)


def apply_updates(updates: list[dict[str, object]]) -> int:
    with LOCK:
        rows = read_rows()
        by_key = {
            (row["query_id"], row["candidate_product_id"]): row
            for row in rows
        }
        changed = 0
        for update in updates:
            key = (
                str(update.get("query_id", "")),
                str(update.get("candidate_product_id", "")),
            )
            row = by_key.get(key)
            if row is None:
                continue
            for field in EDITABLE:
                if field in update:
                    row[field] = str(update[field] or "")
            changed += 1
        if changed:
            write_rows(rows)
        return changed


class ReviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REVIEW_DIR), **kwargs)

    def send_json(self, value: object, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/reviews":
            rows = read_rows()
            self.send_json([
                {
                    "query_id": row["query_id"],
                    "candidate_product_id": row["candidate_product_id"],
                    **{field: row.get(field, "") for field in EDITABLE},
                }
                for row in rows
            ])
            return
        super().do_GET()

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            updates = payload.get("rows", []) if self.path == "/api/sync" else [payload]
            if self.path not in {"/api/save", "/api/sync"} or not isinstance(updates, list):
                self.send_json({"error": "invalid request"}, 400)
                return
            self.send_json({"updated": apply_updates(updates)})
        except Exception as exc:
            self.send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Hybrid review UI and persist changes to CSV.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ReviewHandler)
    print(f"Review UI: http://{args.host}:{args.port}/hybrid_ground_truth_review.html")
    print(f"Saving to: {CSV_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
