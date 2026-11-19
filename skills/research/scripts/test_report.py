"""Self-check for report.py: python3 test_report.py"""
import json
import os
import subprocess
import sys
import tempfile

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.py")


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    with tempfile.TemporaryDirectory() as d:
        write(f"{d}/sources.md", """# Sources

## S001 — Wiki
- Published: last edited 2026-11-17
- Rating: B — wiki
- Origin: own

## S002 — Leak repost
- Published: 2026-05-28
- Rating: D — repost
- Origin: xhs-leak

## S003 — Leak article
- Published: 2026-05-30
- Rating: C — article
- Origin: xhs-leak

## S004 — Publisher
- Published: 2026-06-08
- Rating: A — primary
- Origin: own

## S005 — No rating yet
- Published:
- Rating:
- Origin:
""")
        write(f"{d}/claims.md", """# Claims

## C001 — rumor, two reposts of one leak
- Credibility: 1 — wrongly high
- Supports:
  - S002 `a`
  - S003 `b`
- As of: 2026-05-30

## C002 — primary-backed
- Credibility: 1 — publisher
- Supports:
  - S004 `c`
- As of: 2026-11-19

## C003 — wiki fact from two different origins
- Credibility: 1 — two origins
- Supports:
  - S001 `d` (origin: sega-aug)
  - S001 `e` (origin: famitsu)
- As of: 2026-11-17

## C004 — single wiki fact
- Credibility: 1 — wrongly high
- Supports: S001 `f`
- As of: 2026-11-17

## C005 — unused rumor
- Credibility: 3 — leak
- Supports:
  - S003 `g`
- As of: 2026-05-30
""")
        write(f"{d}/draft.md", "<!-- claims: C001,\n C005 -->\nText [C001]. More [C002, C003].\nAnd [C004] [C009].\n")
        r = subprocess.run([sys.executable, REPORT, d], capture_output=True, text=True)
        out = r.stdout
        assert r.returncode == 1, out
        assert "C001: credibility 1, but one origin (xhs-leak) and no A-rated source" in out, out
        assert "C002: As of 2026-11-19 is newer than any evidence (2026-06-08)" in out, out
        assert "C003: credibility" not in out, out          # two origins from one source is fine
        assert "C004: credibility 1, but one origin (S001)" in out, out
        assert "S005: no Rating letter" in out and "S005: no Origin" in out, out
        assert "draft: unknown claim C009" in out, out
        assert "xhs-leak: S002, S003" in out and "Not used in draft: C005" in out, out
        s = json.load(open(f"{d}/summary.json", encoding="utf-8"))
        assert s["claims"]["C003"]["origins"] == ["sega-aug", "famitsu"], s["claims"]["C003"]
        assert s["claims"]["C002"]["draft_lines"] == [3] and s["sources"]["S003"]["claims"] == ["C001", "C005"]
    print("ok")


if __name__ == "__main__":
    main()
