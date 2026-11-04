from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
API = "http://127.0.0.1:8002"
PORT = 8091

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        clean = urlsplit(path).path.lstrip("/")
        prefix = "ui-faith-v2-unified/"
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
        return str(ROOT / clean)

    def do_GET(self):
        path = urlsplit(self.path).path

        if path == "/":
            self.send_response(302)
            self.send_header(
                "Location",
                "/ui-faith-v2-unified/layout.html"
            )
            self.end_headers()
            return

        if path.startswith(("/auth/", "/api/")):
            return self.proxy()

        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path.startswith(("/auth/", "/api/")):
            return self.proxy()
        self.send_error(404)

    def proxy(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None

        headers = {}
        for key in ("Authorization", "Content-Type", "Accept"):
            if self.headers.get(key):
                headers[key] = self.headers[key]

        request = Request(
            API + self.path,
            data=body,
            headers=headers,
            method=self.command
        )

        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error
        except URLError:
            self.send_error(502, "V2 backend unavailable")
            return

        with response:
            payload = response.read()
            self.send_response(response.status)
            self.send_header(
                "Content-Type",
                response.headers.get(
                    "Content-Type",
                    "application/json"
                )
            )
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

print(f"XynaFaith V2 preview running on {PORT}", flush=True)

ThreadingHTTPServer(
    ("127.0.0.1", PORT),
    Handler
).serve_forever()
