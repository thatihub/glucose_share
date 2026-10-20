#!/usr/bin/env python3
"""Standalone glucose share server — serves ONLY the glucose page.

Whitelist:
  / , /index.html          -> share index.html (no nav)
  /glucose_data.js         -> live data from main project dir
  /glucose_view.js         -> view logic from main project dir
  /static/*                -> CSS/JS assets from main project dir
  /api/dexcom/*            -> proxied to main server (localhost:3002) for Sync
Everything else -> 404. The rest of the health manager is NOT accessible.
"""
import http.server
import socketserver
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

MAIN_DIR = Path.home() / "Documents/Health/personal_health_manager"
SHARE_DIR = Path.home() / "Documents/Health/glucose-share"
MAIN_PORT = 3002
SHARE_PORT = 3003

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "GlucoseShare/1.0"

    def log_message(self, fmt, *args):
        print(fmt % args)

    def do_GET(self):
        self.handle_req(proxy_body=False)

    def do_POST(self):
        self.handle_req(proxy_body=True)

    def handle_req(self, proxy_body):
        raw = self.path
        path = urlparse(raw).path
        # Log raw path for debugging funnel issues
        with open(SHARE_DIR / "paths.log", "a") as f:
            f.write(f"{raw} -> {path}\n")

        # Dexcom API -> proxy to main server so Sync works
        if path.startswith("/api/dexcom/"):
            self.proxy_api(proxy_body)
            return

        # Static assets from main project dir
        if path.startswith("/static/"):
            fpath = (MAIN_DIR / path.lstrip("/")).resolve()
            if MAIN_DIR.resolve() in fpath.parents and fpath.is_file():
                self.serve_file(fpath)
                return
            self.send_error(404, "Not shared")
            return

        # Page + data + view logic
        if path in ("/", "/index.html", "/glucose.html", "/glucose"):
            self.serve_file(SHARE_DIR / "index.html")
            return
        if path == "/glucose_data.js":
            self.serve_file(MAIN_DIR / "glucose_data.js")
            return
        if path == "/glucose_view.js":
            self.serve_file(MAIN_DIR / "glucose_view.js")
            return
        # Extra sections at the bottom of the share page: body composition pills
        # (InBody) and the blood pressure three-month comparison.
        if path in ("/dexa_data.js", "/home_weight_reference.js", "/bp_data.js", "/bp_comparison.js"):
            self.serve_file(MAIN_DIR / path.lstrip("/"))
            return

        self.send_error(404, "Not shared")

    def serve_file(self, fpath):
        try:
            data = fpath.read_bytes()
        except OSError:
            self.send_error(404, "Not found")
            return
        ctype = MIME.get(fpath.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def proxy_api(self, with_body):
        url = f"http://localhost:{MAIN_PORT}{self.path}"
        body = None
        if with_body:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else None
        req = urllib.request.Request(url, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length"):
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                self.send_response(resp.status)
                ctype = resp.headers.get("Content-Type", "application/json")
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_error(e.code, e.reason)
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")


if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("127.0.0.1", SHARE_PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        print(f"Glucose share server on http://127.0.0.1:{SHARE_PORT} (glucose page only)")
        httpd.serve_forever()
