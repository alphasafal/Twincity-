#!/usr/bin/env python3
"""Reverse proxy for the public live demo.

Listens on :8080 and routes:
  /api/*  and /ws*  → FastAPI :8000
  everything else   → Next.js :3000

Used as the Cloudflare Tunnel origin for https://twinpilot.webyaar.in
"""

from __future__ import annotations

import http.client
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WEB = ("127.0.0.1", 3000)
API = ("127.0.0.1", 8000)
LISTEN = ("0.0.0.0", 8080)


def _target(path: str) -> tuple[str, int]:
    # FastAPI routes used by the browser and health checks
    if (
        path.startswith("/api")
        or path.startswith("/ws")
        or path.startswith("/docs")
        or path.startswith("/openapi")
        or path.startswith("/health")
        or path.startswith("/ready")
    ):
        return API
    return WEB


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # quieter logs
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _proxy(self) -> None:
        host, port = _target(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length > 0 else None

        conn = http.client.HTTPConnection(host, port, timeout=120)
        # Drop hop-by-hop + encoding negotiation. Force uncompressed upstream
        # bodies so we never forward gzip bytes without Content-Encoding.
        skip = {"host", "content-length", "accept-encoding", "transfer-encoding", "connection"}
        headers = {k: v for k, v in self.headers.items() if k.lower() not in skip}
        headers["Host"] = f"{host}:{port}"
        headers["Accept-Encoding"] = "identity"
        headers["X-Forwarded-Host"] = self.headers.get("Host", "twinpilot.webyaar.in")
        headers["X-Forwarded-Proto"] = "https"
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            payload = resp.read()
            # If an upstream still compresses, decompress before clients see it.
            encoding = (resp.getheader("Content-Encoding") or "").lower()
            if encoding in {"gzip", "x-gzip"}:
                import gzip

                payload = gzip.decompress(payload)
            elif encoding == "deflate":
                import zlib

                try:
                    payload = zlib.decompress(payload)
                except zlib.error:
                    payload = zlib.decompress(payload, -zlib.MAX_WBITS)
            self.send_response(resp.status, resp.reason)
            for k, v in resp.getheaders():
                # Never forward compression/transfer headers — body is plain now.
                if k.lower() in {
                    "transfer-encoding",
                    "connection",
                    "content-encoding",
                    "content-length",
                }:
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
        except (TimeoutError, socket.error, http.client.HTTPException) as exc:
            msg = f"upstream error: {exc}".encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
        finally:
            conn.close()

    def do_GET(self) -> None:
        self._proxy()

    def do_POST(self) -> None:
        self._proxy()

    def do_PUT(self) -> None:
        self._proxy()

    def do_PATCH(self) -> None:
        self._proxy()

    def do_DELETE(self) -> None:
        self._proxy()

    def do_OPTIONS(self) -> None:
        self._proxy()

    def do_HEAD(self) -> None:
        self._proxy()


def main() -> None:
    httpd = ThreadingHTTPServer(LISTEN, Handler)
    print(f"live_demo_proxy listening on http://{LISTEN[0]}:{LISTEN[1]} → web={WEB} api={API}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
