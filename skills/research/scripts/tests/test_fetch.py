"""Self-check for fetch.py against a local server: python3 tests/test_fetch.py"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the scripts live one level up
FETCH = os.path.join(SCRIPTS, "fetch.py")
# Shift_JIS declared only in <meta>, with a cp932-only char (①) and noise that must be dropped.
PAGE = ('<html lang="ja"><head><meta charset="Shift_JIS"><title>テスト: 記事</title>'
        '<script>var s = "SCRIPT_TEXT";</script></head><body><svg><title>ICON</title></svg><svg/>'
        '<h1>見出し</h1><ul><li>一</li><li>二</li></ul><p>これは①テスト&amp;本文です。</p><p>' + "長い文章。" * 100 +
        '</p></body></html>').encode("cp932")


def make_pdf(text):
    """A minimal one-page PDF with text in Helvetica."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)


PDF = make_pdf("Verbatim PDF sentence for the test.")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/doc.pdf"):
            body, ctype = PDF, "application/pdf"
        elif self.path.startswith("/go-to-a"):  # redirect to an already saved page
            self.send_response(302)
            self.send_header("Location", "/a")
            self.end_headers()
            return
        else:
            body, ctype = (b"<html><body>hi</body></html>" if self.path.startswith("/short") else PAGE), "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
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
        assert subprocess.run([sys.executable, os.path.join(os.path.dirname(FETCH), "check_quotes.py"), d, "sources.md"],
                              capture_output=True, text=True).returncode == 0  # fresh hash matches
        assert 'sha256: "' in orig

        r = run(d, base + "/a")
        assert r.returncode == 3 and "S001" in r.stdout, (r.returncode, r.stdout)
        for same in ("/a/", "/a?utm_source=x&fbclid=1#top", "/%61"):
            r = run(d, base + same)
            assert r.returncode == 3 and "S001 already saved" in r.stdout, (same, r.returncode, r.stdout)
        r = run(d, base + "/go-to-a")
        assert r.returncode == 3 and "S001" in r.stdout, (r.returncode, r.stdout, r.stderr)

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

        for same in ("http://www.example.com/x/?utm_medium=y", "https://EXAMPLE.com/x#part"):
            r = run(d, same, "--text-file", pasted)
            assert r.returncode == 3 and "S004" in r.stdout, (same, r.stdout)

        r = run(d, base + "/doc.pdf", "--min-chars", "0")
        if shutil.which("pdftotext") or importlib.util.find_spec("pypdf"):
            assert r.returncode == 0, r.stderr
            pdf = read(d, "sources", "S005", "original.md")
            assert "[page 1]" in pdf and "Verbatim PDF sentence for the test." in pdf, pdf
            assert os.path.exists(os.path.join(d, "sources", "S005", "original.pdf"))
            assert run(d, base + "/doc.pdf").returncode == 3
        else:
            assert r.returncode == 5 and "brew install poppler" in r.stderr, (r.returncode, r.stderr)
            assert not os.path.exists(os.path.join(d, "sources", "S005"))
            print("(no PDF tool installed: checked the refusal path only)")

        index = read(d, "sources.md")
        assert index.startswith("# Sources") and index.count("\n## S") == (5 if os.path.exists(os.path.join(d, "sources", "S005")) else 4)
        assert "## S004 — Pasted\n- URL: https://example.com/x\n" in index
    srv.shutdown()
    print("ok")


if __name__ == "__main__":
    main()
