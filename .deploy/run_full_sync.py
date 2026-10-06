#!/usr/bin/env python3
import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8080"
TERMINAL = {"SUCCEEDED", "FAILED"}
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 1000


def request(method, path, payload=None, token=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {body}") from exc


def login():
    auth = request("POST", "/api/auth/login", {
        "email": "admin@example.com",
        "password": "Admin@123456",
    })
    if "ADMIN" not in auth["user"].get("roles", []):
        raise RuntimeError("Authenticated account is not an ADMIN")
    return auth["access_token"]


token = login()

started_at = time.monotonic()
if len(sys.argv) > 2:
    job_id = sys.argv[2]
    print("SYNC_RESUME=true", flush=True)
else:
    job = request("POST", f"/admin/ai-sync/jobs/limit?limit={LIMIT}", token=token)
    job_id = job["job_id"]
    print(f"SYNC_LIMIT={LIMIT}", flush=True)
print(f"SYNC_JOB_ID={job_id}", flush=True)

deadline = time.monotonic() + 4 * 60 * 60
while True:
    try:
        job = request("GET", f"/admin/ai-sync/jobs/{job_id}", token=token)
    except RuntimeError as error:
        if not str(error).startswith("HTTP 401 "):
            raise
        token = login()
        print("SYNC_TOKEN_REFRESHED=true", flush=True)
        continue
    status = job["status"]
    print(f"SYNC_STATUS={status} checked_at={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}", flush=True)
    if status in TERMINAL:
        print(f"SYNC_ELAPSED_SECONDS={time.monotonic() - started_at:.3f}", flush=True)
        print("SYNC_FINAL=" + json.dumps(job, ensure_ascii=False, separators=(",", ":")), flush=True)
        sys.exit(0 if status == "SUCCEEDED" else 2)
    if time.monotonic() >= deadline:
        raise TimeoutError(f"Sync job {job_id} did not finish within four hours")
    time.sleep(30)
