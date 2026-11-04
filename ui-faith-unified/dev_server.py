from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent

class Handler(SimpleHTTPRequestHandler):
    # DEV_AUTH_PROXY_V1
    def proxy_auth(self):
        path = urlsplit(self.path).path

        allowed = (
            (self.command, path) in {
                ("POST", "/auth/login"),
                ("GET", "/auth/me"),
                ("GET", "/api/v1/faith/sermon/my"),
            }
            or (
                self.command == "POST"
                and path.startswith("/api/v1/faith/ministry/sermons/")
                and path.endswith("/transform")
                and len(path.split("/")) == 8
                and bool(path.split("/")[6])
            )
        )

        if not allowed:
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 16384:
                self.send_error(413)
                return

            body = self.rfile.read(length) if length else None

            headers = {}
            for name in ("Content-Type", "Authorization"):
                value = self.headers.get(name)
                if value:
                    headers[name] = value

            request = Request(
                "http://127.0.0.1:8002" + path,
                data=body,
                headers=headers,
                method=self.command,
            )

            try:
                response = urlopen(request, timeout=15)
            except HTTPError as error:
                response = error

            with response:
                data = response.read(1048577)
                if len(data) > 1048576:
                    self.send_error(502)
                    return

                self.send_response(response.status)
                self.send_header(
                    "Content-Type",
                    response.headers.get(
                        "Content-Type", "application/json"
                    ),
                )
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        except (URLError, TimeoutError, ValueError):
            self.send_error(502, "Development API unavailable")

    def do_POST(self):
        self.proxy_auth()

    def do_GET(self):
        url = urlsplit(self.path).path

        # Forward current-user authentication requests.
        if url in {
            "/auth/me",
            "/api/v1/faith/sermon/my",
        }:
            self.proxy_auth()
            return

        if url == "/layout.html":
            layout = (ROOT / "ui-faith" / "layout.html").read_text()
            script = (
                '<script defer src="/ui-faith-unified/'
                'navigation-bridge.js"></script>'
            )
            if "</body>" not in layout:
                self.send_error(500, "Layout closing tag missing")
                return
            script += (
                '<script defer src="/ui-faith-unified/'
                'auth-bridge.js"></script>'
            )
            layout = layout.replace("</body>", script + "\n</body>", 1)
            body = layout.encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()

    def translate_path(self, path):
        url = urlsplit(path).path

        if url == "/":
            url = "/ui-faith-unified/preview.html"

        # Support the existing V1 layout redirect.
        if url == "/layout.html":
            return str((ROOT / "ui-faith" / "layout.html").resolve())

        # Development-only V1 route mapping.
        if url in ("/faith", "/faith/"):
            return str(ROOT / "ui-faith" / "index.html")

        if url.startswith("/faith/"):
            base = (ROOT / "ui-faith").resolve()
            target = (base / url[len("/faith/"):]).resolve()
            if target.is_relative_to(base) and target.is_file():
                return str(target)

        # Serve only approved frontend directories.
        for prefix, directory in (
            ("/ui-faith-unified/", "ui-faith-unified"),
            ("/ui-faith/", "ui-faith"),
            ("/ui-faith-v2/", "ui-faith-v2"),
        ):
            if url.startswith(prefix):
                base = (ROOT / directory).resolve()
                target = (ROOT / url.lstrip("/")).resolve()

                if target.is_relative_to(base) and target.is_file():
                    return str(target)

        return str(ROOT / "__preview_not_found__")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8090), Handler)
    print("XynaFaith unified preview running on port 8090", flush=True)
    server.serve_forever()
