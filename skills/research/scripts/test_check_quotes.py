"""Self-check for check_quotes.py: python3 test_check_quotes.py"""
import os
import subprocess
import sys
import tempfile

CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_quotes.py")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    with tempfile.TemporaryDirectory() as d:
        write(f"{d}/sources/S001/original.md", '---\ncapture: "script"\n---\n\n発売日・価格：未定\n\nHello   world\nnext line\n')
        write(f"{d}/sources/S003/original.md", '---\ncapture: "model-fetch"\n---\n\nsummary text\n')
        write(f"{d}/sources.md", "# Sources\n\n## S001 — t\n- Key phrases: `発売日・価格：未定`, `Hello world next`\n"
                                 "  - `missing phrase`\n\n## S003 — t\n- Key phrases: `summary text`\n")
        write(f"{d}/claims.md", "## C001 — x\n- Supports: S001 `world next line`, S001: `Hello world`\n"
                                "- Contradicts: S002 `anything`\n- Note: bare `code` outside S sections is ignored\n")
        r = subprocess.run([sys.executable, CHECK, d], capture_output=True, text=True)
        out = r.stdout
        assert r.returncode == 1, out
        assert "sources.md:5: NOT FOUND in S001: `missing phrase`" in out, out
        assert "claims.md:3: S002 has no original.md" in out, out
        assert "WARNING S003 is model-fetch" in out, out
        assert "7 quotes checked, 2 problems" in out, out

        r = subprocess.run([sys.executable, CHECK, d, "claims.md"], capture_output=True, text=True)
        assert "3 quotes checked, 1 problems" in r.stdout, r.stdout
    print("ok")


if __name__ == "__main__":
    main()
