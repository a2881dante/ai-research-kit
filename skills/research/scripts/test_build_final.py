"""Self-check for build_final.py: python3 test_build_final.py"""
import os
import subprocess
import sys
import tempfile

BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_final.py")


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    with tempfile.TemporaryDirectory() as d:
        write(f"{d}/STATE.md", "# State\n\n- User language: русский\n")
        write(f"{d}/sources.md", "# Sources\n\n## S001 — Wiki\n- URL: https://w.example/a\n"
                                 "- Archive: http://web.archive.org/web/1/https://w.example/a (existing snapshot)\n\n"
                                 "## S002 — セガ\n- URL: https://sega.example/\n- Archive: none\n")
        write(f"{d}/claims.md", "# Claims\n\n## C001 — a\n- Supports:\n  - S001 `x`\n- Contradicts:\n  - S002 `y`\n\n"
                                "## C002 — b\n- Supports: S002 `z`, S001 `w`\n\n## C003 — empty\n- Supports:\n- Contradicts:\n")
        write(f"{d}/draft.md", "# Title\n\n<!-- working\n note -->\n\n## Part\n<!-- claims: C001 -->\n\n"
                               "Fact one [C001]. Fact two [C001, C002]. Again [C001].\n"
                               "Quote: S002 `新しい物語` — «новая история» (перевод). Native: S001 `plain words`. See [S002].\n\n"
                               "## Sources\n\n- S001 — Wiki — rating B\n")
        r = subprocess.run([sys.executable, BUILD, d], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        with open(f"{d}/final.md", encoding="utf-8") as f:
            out = f.read()
        assert "<!--" not in out and "rating B" not in out and "`" not in out and "[C0" not in out, out
        assert "Fact one[^1]. Fact two[^2]. Again[^1]." in out, out
        assert "Quote: «новая история»[^3]. Native: «plain words»[^1]. See[^4]." in out, out
        assert "[^1]: Wiki — https://w.example/a (архив: http://web.archive.org/web/1/https://w.example/a)\n" in out, out
        assert "[^2]: Wiki — https://w.example/a (архив: http://web.archive.org/web/1/https://w.example/a); セガ — https://sega.example/\n" in out, out
        assert "[^3]: Оригинал: «新しい物語» — セガ — https://sega.example/\n" in out, out
        assert "S002" not in out.split("[^1]:")[0], out  # contradicting sources are not cited

        write(f"{d}/draft.md", "Bad [C009] and [C003].\n")
        r = subprocess.run([sys.executable, BUILD, d], capture_output=True, text=True)
        assert r.returncode == 1 and "unknown claim C009" in r.stderr and "C003 has no Supports" in r.stderr, r.stderr
    print("ok")


if __name__ == "__main__":
    main()
