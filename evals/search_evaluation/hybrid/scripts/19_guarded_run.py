"""Bounded evaluation supervisor with durable stdout and exit status.

Use docker exec -d to start; inspect the status/log with short read-only calls.
No credentials are copied to the log or status. Intended for evaluation scripts,
not for supervising the main application.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("script", type=Path)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    status_path = args.output / "status.json"
    if status_path.exists():
        raise FileExistsError(status_path)
    status = {"started_at": datetime.now(timezone.utc).isoformat(), "state": "running", "supervisor_pid": os.getpid(), "timeout_seconds": args.timeout}
    with (args.output / "progress.log").open("w", encoding="utf-8", buffering=1) as log:
        child = subprocess.Popen([sys.executable, "-u", str(args.script), *args.arguments], stdout=log, stderr=subprocess.STDOUT)
        status["child_pid"] = child.pid
        status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
        try:
            status["exit_code"] = child.wait(timeout=args.timeout)
            status["state"] = "completed" if status["exit_code"] == 0 else "failed"
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
            status["exit_code"] = child.returncode
            status["state"] = "timed_out"
        finally:
            status["finished_at"] = datetime.now(timezone.utc).isoformat()
            status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
