"""Local-only XynaFaith unified V2 preview.

Static frontend: /ui-faith-v2-unified/
API forwarding: /api/* -> http://127.0.0.1:8002
"""

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import mimetypes
import os

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = (ROOT / "ui-faith-v2-unified").resolve()
API_ORIGIN = "http://127.0.0.1:8002"
PREFIX = "/ui-faith-v2-unified/"
PORT = 8091


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PUT(self):
        self.handle_request()

    def do_PATCH(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def handle_request(self):
        parsed = urlsplit(self.path)
        path = parsed.path

        if path.startswith(("/api/", "/auth/")):
            return self.proxy_api()

        if self.command != "GET":
            self.send_error(405)
            return

        if path in ("/", "/layout.html"):
            target = FRONTEND / "layout.html"
        elif path == "/index.html":
            target = FRONTEND / "layout.html"
        elif path.startswith(PREFIX):
            relative = path[len(PREFIX):]
            target = (FRONTEND / relative).resolve()
        elif path.startswith("/faith/"):
            legacy = (ROOT / "ui-faith").resolve()
            relative = path[len("/faith/"):]
            target = (legacy / relative).resolve()

            if not target.is_relative_to(legacy):
                self.send_error(403)
                return
        else:
            self.send_error(404)
            return

        if not target.is_relative_to(FRONTEND):
            self.send_error(403)
            return

        if not target.is_file():
            self.send_error(404)
            return

        content = target.read_bytes()
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def proxy_api(self):
        target = API_ORIGIN + self.path
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None

        headers = {}
        for name in ("Authorization", "Content-Type", "Accept"):
            value = self.headers.get(name)
            if value:
                headers[name] = value

        request = Request(
            target,
            data=body,
            headers=headers,
            method=self.command,
        )

        try:
            with urlopen(request, timeout=30) as response:
                self.send_proxy_response(response)
        except HTTPError as error:
            self.send_proxy_response(error)
        except URLError:
            self.send_error(502, "Development API unavailable")

    def send_proxy_response(self, response):
        data = response.read()
        self.send_response(response.status)

        for name in ("Content-Type", "Cache-Control"):
            value = response.headers.get(name)
            if value:
                self.send_header(name, value)

        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    if not FRONTEND.is_dir():
        raise SystemExit("Unified V2 frontend directory missing")

    print(f"XynaFaith V2 preview: http://127.0.0.1:{PORT}/")
    print("Development API:", API_ORIGIN)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
