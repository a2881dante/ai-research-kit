"""Self-check for fetch.py against a local server: python3 test_fetch.py"""
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FETCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch.py")
# Shift_JIS declared only in <meta>, with a cp932-only char (①) and noise that must be dropped.
PAGE = ('<html lang="ja"><head><meta charset="Shift_JIS"><title>テスト: 記事</title>'
        '<script>var s = "SCRIPT_TEXT";</script></head><body><svg><title>ICON</title></svg><svg/>'
        '<h1>見出し</h1><ul><li>一</li><li>二</li></ul><p>これは①テスト&amp;本文です。</p><p>' + "長い文章。" * 100 +
        '</p></body></html>').encode("cp932")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><body>hi</body></html>" if self.path.startswith("/short") else PAGE
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def run(*args):
    return subprocess.run([sys.executable, FETCH, *args, "--no-archive"], capture_output=True, text=True)


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    with tempfile.TemporaryDirectory() as d:
        r = run(d, base + "/a")
        assert r.returncode == 0, r.stderr
        orig = read(d, "sources", "S001", "original.md")
        assert "これは①テスト&本文です。" in orig, orig[:500]
        assert "# 見出し" in orig and "- 一\n- 二" in orig
        assert "SCRIPT_TEXT" not in orig and "ICON" not in orig
        assert 'lang: "ja"' in orig and 'title: "テスト: 記事"' in orig and 'charset: "cp932"' in orig
        assert os.path.exists(os.path.join(d, "sources", "S001", "raw.html"))

        r = run(d, base + "/a")
        assert r.returncode == 3 and "S001" in r.stdout, (r.returncode, r.stdout)

        r = run(d, base + "/ページ?q=日本")
        assert r.returncode == 0, r.stderr

        r = run(d, base + "/short")
        assert r.returncode == 4 and not os.path.exists(os.path.join(d, "sources", "S003"))
        assert run(d, base + "/short", "--min-chars", "0").returncode == 0

        pasted = os.path.join(d, "paste.txt")
        with open(pasted, "w", encoding="utf-8") as f:
            f.write("Текст, вставлений користувачем.\n")
        r = run(d, "https://example.com/x", "--text-file", pasted, "--capture", "user-paste", "--title", "Pasted")
        assert r.returncode == 0, r.stderr
        assert 'capture: "user-paste"' in read(d, "sources", "S004", "original.md")

        index = read(d, "sources.md")
        assert index.startswith("# Sources") and index.count("\n## S") == 4
        assert "## S004 — Pasted\n- URL: https://example.com/x\n" in index
    srv.shutdown()
    print("ok")


if __name__ == "__main__":
    main()
