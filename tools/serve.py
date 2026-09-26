#!/usr/bin/env python3
"""
Local preview server that behaves like Cloudflare Pages, so you can test the
site exactly as it will run in production:

  * /blog            -> serves blog.html        (extension-less URLs)
  * /blog.html       -> 308 redirect to /blog    (same as Pages)
  * unknown paths    -> 404.html with status 404
  * every header in public/_headers is applied, INCLUDING the strict CSP,
    so a CSP violation shows up in your browser console before you deploy.

    python tools/serve.py            # http://localhost:8080
    python tools/serve.py 9000       # custom port

Standard library only. Binds to 127.0.0.1 so it is never exposed to your LAN.
"""
import fnmatch
import http.server
import pathlib
import posixpath
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent / "public"


def load_headers():
    rules, cur = [], None
    f = ROOT / "_headers"
    if not f.exists():
        return rules
    for raw in f.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw[0].isspace():
            cur = (raw.strip(), [])
            rules.append(cur)
        elif cur and ":" in raw:
            k, v = raw.strip().split(":", 1)
            cur[1].append((k.strip(), v.strip()))
    return rules


RULES = load_headers()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def end_headers(self):
        path = urllib.parse.urlsplit(self.path).path
        for pattern, headers in RULES:
            if fnmatch.fnmatch(path, pattern):
                for k, v in headers:
                    # upgrade-insecure-requests breaks plain-http localhost
                    if k.lower() == "content-security-policy":
                        v = v.replace("; upgrade-insecure-requests", "")
                    if k.lower() == "strict-transport-security":
                        continue
                    self.send_header(k, v)
        super().end_headers()

    def do_HEAD(self):
        if self.route(head=True):
            return super().do_HEAD()

    def do_GET(self):
        if self.route():
            return super().do_GET()

    def route(self, head=False):
        """Rewrite self.path like Cloudflare Pages. Returns False if a response was already sent."""
        parts = urllib.parse.urlsplit(self.path)
        path = posixpath.normpath(urllib.parse.unquote(parts.path))
        if parts.path.endswith("/") and path != "/":
            path += "/"
        target = ROOT / path.lstrip("/")
        # *.html -> extension-less (Cloudflare Pages behaviour)
        if path.endswith(".html"):
            clean = path[:-5]
            if clean.endswith("/index"):
                clean = clean[:-5]
            self.send_response(308)
            self.send_header("Location", clean + (("?" + parts.query) if parts.query else ""))
            self.end_headers()
            return False
        if path == "/":
            self.path = "/index.html"
        elif target.is_file():
            pass
        elif (ROOT / (path.lstrip("/") + ".html")).is_file():
            self.path = path + ".html"
        elif (target / "index.html").is_file():
            self.path = path.rstrip("/") + "/index.html"
        else:
            self.send_response(404)
            body = (ROOT / "404.html").read_bytes()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head:
                self.wfile.write(body)
            return False
        return True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"serving {ROOT} on http://localhost:{port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
