#!/usr/bin/env python3
from __future__ import annotations

import socket
from typing import Any


HOST = "10.3.147.211"
PORT = 6379


def read_response(stream: Any) -> Any:
    prefix = stream.read(1)
    if not prefix:
        raise EOFError("Redis closed the connection")
    line = stream.readline().removesuffix(b"\r\n")
    if prefix == b"+":
        return line.decode()
    if prefix == b"-":
        raise RuntimeError(line.decode())
    if prefix == b":":
        return int(line)
    if prefix == b"$":
        length = int(line)
        if length == -1:
            return None
        value = stream.read(length).decode()
        stream.read(2)
        return value
    if prefix == b"*":
        return [read_response(stream) for _ in range(int(line))]
    raise RuntimeError(f"Unsupported Redis response prefix: {prefix!r}")


def command(*parts: str) -> Any:
    payload = f"*{len(parts)}\r\n" + "".join(
        f"${len(part.encode('utf-8'))}\r\n{part}\r\n" for part in parts
    )
    with socket.create_connection((HOST, PORT), timeout=5) as connection:
        connection.sendall(payload.encode())
        return read_response(connection.makefile("rb"))


existing = set(command("FT._LIST"))

if "checkpoint" not in existing:
    result = command(
        "FT.CREATE", "checkpoint", "ON", "JSON", "PREFIX", "1", "checkpoint:",
        "SCHEMA",
        "$.thread_id", "AS", "thread_id", "TAG", "SEPARATOR", ",",
        "$.run_id", "AS", "run_id", "TAG", "SEPARATOR", ",",
        "$.checkpoint_ns", "AS", "checkpoint_ns", "TAG", "SEPARATOR", ",",
        "$.checkpoint_id", "AS", "checkpoint_id", "TAG", "SEPARATOR", ",",
        "$.parent_checkpoint_id", "AS", "parent_checkpoint_id", "TAG", "SEPARATOR", ",",
        "$.checkpoint_ts", "AS", "checkpoint_ts", "NUMERIC",
        "$.source", "AS", "source", "TAG", "SEPARATOR", ",",
        "$.step", "AS", "step", "NUMERIC",
        "$.has_writes", "AS", "has_writes", "TAG", "SEPARATOR", ",",
    )
    print(f"checkpoint={result}")

if "checkpoint_write" not in existing:
    result = command(
        "FT.CREATE", "checkpoint_write", "ON", "JSON", "PREFIX", "1", "checkpoint_write:",
        "SCHEMA",
        "$.thread_id", "AS", "thread_id", "TAG", "SEPARATOR", ",",
        "$.checkpoint_ns", "AS", "checkpoint_ns", "TAG", "SEPARATOR", ",",
        "$.checkpoint_id", "AS", "checkpoint_id", "TAG", "SEPARATOR", ",",
        "$.task_id", "AS", "task_id", "TAG", "SEPARATOR", ",",
        "$.idx", "AS", "idx", "NUMERIC",
        "$.channel", "AS", "channel", "TAG", "SEPARATOR", ",",
        "$.type", "AS", "type", "TAG", "SEPARATOR", ",",
    )
    print(f"checkpoint_write={result}")

print("indexes=" + ",".join(command("FT._LIST")))
