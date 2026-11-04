"""Раздача собранного frontend и прокси /api на backend для локального демо.

Vite dev-сервер удобен для разработки, но для показа с телефона достаточно
собранного dist: этот скрипт отдаёт SPA, включает fallback на index.html и
проксирует API на 127.0.0.1:8000.
"""

from __future__ import annotations

import argparse
import http.client
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "dist"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "ConsultFlowDemo/1.0"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        print(f"{self.address_string()} - {format % args}")

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        connection = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=60)
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "connection"}
        }
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() in {"transfer-encoding", "connection", "content-length"}:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        finally:
            connection.close()

    def _static(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            path = "/index.html"
        target = (ROOT / path.lstrip("/")).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            self.send_error(403)
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            # SPA: /client, /orders и другие маршруты отдают index.html.
            target = ROOT / "index.html"
        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/") or self.path == "/api":
            self._proxy()
        else:
            self._static()

    def do_HEAD(self) -> None:  # noqa: N802
        self._static()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def do_PUT(self) -> None:  # noqa: N802
        self._proxy()

    def do_PATCH(self) -> None:  # noqa: N802
        self._proxy()

    def do_DELETE(self) -> None:  # noqa: N802
        self._proxy()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._proxy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Локальная раздача ConsultFlow")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5173)
    args = parser.parse_args()
    if not (ROOT / "index.html").is_file():
        raise SystemExit("Сначала соберите frontend: cd frontend && npm run build")
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"ConsultFlow demo: http://127.0.0.1:{args.port}/")
    print(f"Prototype:       http://127.0.0.1:{args.port}/prototype/")
    server.serve_forever()


if __name__ == "__main__":
    main()
