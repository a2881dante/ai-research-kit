"""Self-check for report.py: python3 tests/test_report.py"""
import json
import os
import subprocess
import sys
import tempfile

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the scripts live one level up
REPORT = os.path.join(SCRIPTS, "report.py")


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

## S006 — Free-text origin
- Published: 2026-11-16 (snapshot 2026-11-17)
- Rating: B — press
- Origin: Rockstar (launch time), PlayStation guide
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

## C006 — overtaken by later news
- Credibility: 2 — press
- Supports:
  - S004 `h`
- Contradicts:
  - S006 `i`
""")
        write(f"{d}/draft.md", "<!-- claims: C001,\n C005 -->\nText [C001]. More [C002, C003].\nAnd [C004] [C009].\nKnown [CK].\n")
        write(f"{d}/STATE.md", "# State\n\n- User language: English\n")
        write(f"{d}/factcheck-log.md", "## 2026-11-19 — S001-S003, C001\n- Result: S001 -> B; C002 -> 1; C003-C004 -> 1\n")
        write(f"{d}/final.md", "hand-written final\n")
        r = subprocess.run([sys.executable, REPORT, d], capture_output=True, text=True)
        out = r.stdout
        assert r.returncode == 1, out
        assert "C001: credibility 1, but one origin (xhs-leak) and no A-rated source" in out, out
        assert "C002: As of 2026-11-19 is newer than any supporting evidence (2026-06-08)" in out, out
        assert "S006: Origin should be one short label" in out, out
        assert "C006: contradicting evidence is newer than any support (S006 2026-11-16)" in out, out
        assert "C003  1  as of 2026-11-17" in out, out
        assert "STATE.md has no Settings block" in out, out
        assert "S001: Published should start with the date" in out and "S002: Published" not in out, out
        assert "rated but never mentioned in factcheck-log.md: S004, S006, C005, C006" in out, out
        assert "final.md can't be rebuilt from draft.md: unknown claim C009" in out, out
        assert "C003: credibility" not in out, out          # two origins from one source is fine
        assert "C004: credibility 1, but one origin (S001)" in out, out
        assert "S005: no Rating letter" in out and "S005: no Origin" in out, out
        assert "draft: unknown claim C009" in out, out
        assert "Common-knowledge facts [CK], not checked: draft lines 5" in out, out
        assert "xhs-leak: S002, S003" in out and "Not used in draft: C005, C006" in out, out
        s = json.load(open(f"{d}/summary.json", encoding="utf-8"))
        assert s["claims"]["C003"]["origins"] == ["sega-aug", "famitsu"], s["claims"]["C003"]
        assert s["claims"]["C002"]["draft_lines"] == [3] and s["sources"]["S003"]["claims"] == ["C001", "C005"]
        write(f"{d}/draft.md", "Text [C001].\n")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(REPORT), "build_final.py"), d], check=True,
                       capture_output=True)
        assert "final.md differs" not in subprocess.run([sys.executable, REPORT, d], capture_output=True, text=True).stdout
        with open(f"{d}/final.md", "a", encoding="utf-8") as f:
            f.write("A hand edit.\n")
        assert "final.md differs" in subprocess.run([sys.executable, REPORT, d], capture_output=True, text=True).stdout
    print("ok")


if __name__ == "__main__":
    main()
