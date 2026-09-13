"""Stop only this evaluation's temporary uvicorn processes inside Docker.

Never targets the original service on port 8000. No filesystem deletion.
"""
import argparse
import os
from pathlib import Path
import signal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ports", nargs="+", type=int, required=True)
    args = parser.parse_args()
    if any(port not in range(8001, 8010) for port in args.ports):
        raise ValueError("Only temporary probe ports 8001..8009 are allowed")
    stopped = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            argv = (path / "cmdline").read_bytes().split(b"\x00")
            environment = (path / "environ").read_bytes().split(b"\x00")
            if b"uvicorn" not in argv or b"ecommerce_search_assistant.main:app" not in argv:
                continue
            if b"PYTHONPATH=/tmp/hybrid-src" not in environment or b"--port" not in argv:
                continue
            port = int(argv[argv.index(b"--port") + 1])
            if port in args.ports:
                os.kill(int(path.name), signal.SIGTERM)
                stopped.append({"pid": int(path.name), "port": port})
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    print(stopped)


if __name__ == "__main__":
    main()
