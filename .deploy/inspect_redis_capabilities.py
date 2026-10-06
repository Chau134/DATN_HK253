#!/usr/bin/env python3
import socket


HOST = "10.3.147.211"
PORT = 6379


def run(*parts: str) -> None:
    payload = f"*{len(parts)}\r\n" + "".join(
        f"${len(part.encode('utf-8'))}\r\n{part}\r\n" for part in parts
    )
    chunks: list[bytes] = []
    with socket.create_connection((HOST, PORT), timeout=5) as connection:
        connection.settimeout(0.5)
        connection.sendall(payload.encode("utf-8"))
        while True:
            try:
                chunk = connection.recv(65536)
            except TimeoutError:
                break
            if not chunk:
                break
            chunks.append(chunk)
    print(" ".join(parts), repr(b"".join(chunks).decode("utf-8", errors="replace")))


run("MODULE", "LIST")
run("FT._LIST")
run("COMMAND", "INFO", "FT.CREATE")
