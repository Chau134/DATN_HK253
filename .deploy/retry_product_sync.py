#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8080"
PRODUCT_ID = sys.argv[1]


def request(method, path, payload=None, token=None, timeout=900):
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


auth = request("POST", "/api/auth/login", {
    "email": "admin@example.com",
    "password": "Admin@123456",
})
token = auth["access_token"]
result = request("POST", f"/admin/ai-sync/products/{PRODUCT_ID}", token=token)
print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))

failed = int(result.get("failed_count", 0))
image_failed = int(result.get("image_failed_count", 0))
sys.exit(0 if failed == 0 and image_failed == 0 else 2)
