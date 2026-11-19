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


def check(*args):
    return subprocess.run([sys.executable, CHECK, *args], capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as d:
        write(f"{d}/sources/S001/original.md", '---\ncapture: "script"\n---\n\n発売日・価格：未定\n\nHello   world\nnext line\n')
        write(f"{d}/sources/S003/original.md", '---\ncapture: "model-fetch"\n---\n\nsummary text\n')
        write(f"{d}/sources.md", "# Sources\n\n## S001 — t\n- Key phrases: `発売日・価格：未定`, `Hello world next`\n"
                                 "  - `missing phrase`\n\n## S003 — t\n- Key phrases: `summary text`\n"
                                 "- Notes: same origin as S001/S004\n")
        write(f"{d}/claims.md", "## C001 — x\n- Credibility: 1 — ok\n- Supports: S001 `world next line`, S001: `Hello world`\n"
                                "- Contradicts: S002 `anything`\n- Note: bare `code` outside S sections is ignored\n\n"
                                "## C002 — rumor\n- Credibility: 3 — leak\n")
        r = check(d)
        out = r.stdout
        assert r.returncode == 1, out
        assert "sources.md:5: NOT FOUND in S001: `missing phrase`" in out, out
        assert "sources.md:9: unknown source S004" in out and "unknown source S001" not in out, out
        assert "claims.md:4: S002 has no original.md" in out and "unknown source S002" not in out, out
        assert "WARNING S003 is model-fetch" in out, out
        assert "7 quotes checked, 3 problems" in out, out

        assert "3 quotes checked, 1 problems" in check(d, "claims.md").stdout

        write(f"{d}/draft.md", "# Draft\n\nAnnounced [C001]. Leak says September [C002], also [C002, C009].\n"
                               "Quote: S001 `発売日・価格：未定` — «дата и цена не определены» (перевод).\n")
        r = check(d, "draft.md")
        assert "draft.md:3: unknown claim C009" in r.stdout, r.stdout
        assert "  C002 (3): draft.md:3" in r.stdout, r.stdout
        assert "C001 (" not in r.stdout, r.stdout
        assert "1 quotes checked, 1 problems" in r.stdout, r.stdout
        write(f"{d}/cut.md", "S001 `Hello [...] next line` ok, S001 `next line […] Hello` wrong order\n")
        r = check(d, "cut.md")
        assert "NOT FOUND in S001: `next line […] Hello`" in r.stdout and "2 quotes checked, 1 problems" in r.stdout, r.stdout

        write(f"{d}/sources/S001/translation.ru.md", "---\nsource: S001\n---\n\n**Not authoritative.**\n\n"
                                                     "> 発売日・価格：未定\nДата и цена: не определены. `ignored` S999\n\n"
                                                     "> Hello world next line\nПривет.\n\n> Hello brave world\nПривет, мир.\n")
        r = check(d, "sources/S001/translation.ru.md")
        assert "translation.ru.md:13: original paragraph not found in S001: Hello brave world" in r.stdout, r.stdout
        assert "3 quotes checked, 1 problems" in r.stdout, r.stdout
        assert "translation.ru.md:13" in check(d).stdout
        # Same words, different encoding: NFD ї, full-width colon, NBSP, soft hyphen, curly quotes, em dash.
        os.makedirs(f"{d}/sources/S005")
        write(f"{d}/sources/S005/original.md",
              '---\ncapture: "script"\n---\n\nКиїв： “so­ft” — ok\n')
        write(f"{d}/uni.md", 'S005 `Київ: "soft" - ok`, S005 `Київ: hard`\n')
        r = check(d, "uni.md")
        assert "2 quotes checked, 1 problems" in r.stdout and "`Київ: hard`" in r.stdout, r.stdout
    print("ok")


if __name__ == "__main__":
    main()
