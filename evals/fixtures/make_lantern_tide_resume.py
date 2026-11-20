#!/usr/bin/env python3
"""Build a half-assessed "Lantern Tide" research folder: a session that stopped mid-assessment.

  python3 evals/fixtures/make_lantern_tide_resume.py <out_dir>

Starts from the small fixture and adds work from an earlier session, with planted mistakes:
  - C002 says the price is $29.99 with credibility 1 (a press error; the official price is $24.99)
  - C003, the PS5 rumor, has credibility 1 although its three sources share one origin
  - C004 has a hand-written As of newer than its evidence
And a preference that exists only on disk (STATE.md): the article is in Ukrainian and must not
mention the budget.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

RATED = {  # sid: (rating, origin)
    "S001": ("A — the studio's own press release (log 2026-11-10)", "own"),
    "S002": ("B — established outlet retelling the press release (log 2026-11-10)", "kumoforge"),
    "S005": ("D — anonymous board post, second-hand claim (log 2026-11-10)", "board-2026-10"),
    "S006": ("C — aggregator retelling the board post, says unverified (log 2026-11-10)", "board-2026-10"),
    "S007": ("D — blog retelling LeakHub without caveats (log 2026-11-10)", "board-2026-10"),
    "S008": ("A — the official store page (log 2026-11-10)", "own"),
}

CLAIMS = """\
# Claims

## C001 — Lantern Tide launches March 12, 2027 on PC and Switch 2
- Q: Q1
- Credibility: 1 — the studio's release and store page
- Origin: Kumo Forge
- Supports:
  - S001 `will launch on March 12, 2027 for PC (Steam) and Nintendo Switch 2`
  - S008 `Release date: Mar 12, 2027`
- Contradicts:

## C002 — The price is $29.99
- Q: Q1
- Credibility: 1 — reported by an established outlet
- Origin: Kumo Forge announcement
- Supports:
  - S002 `The game will cost $29.99, according to the announcement.`
- Contradicts:

## C003 — A PS5 version comes in 2028
- Q: Q3
- Credibility: 1 — reported by three sites
- Origin: Japanese message board
- Supports:
  - S005 `PS5版は2028年に出るらしい。`
  - S006 `Lantern Tide will come to PS5 in 2028`
  - S007 `Lantern Tide вийде на PS5 у 2028 році`
- Contradicts:

## C004 — The director is Aiko Mura
- Q: Q2
- Credibility: 1 — the studio's release
- Origin: Kumo Forge
- Supports:
  - S001 `directed by Aiko Mura`
- Contradicts:
- As of: 2026-11-19
"""

LOG = """\
# Fact-check log

<!-- Append-only, newest at the bottom. Never rewrite old entries: a changed rating gets a new entry. -->

## 2026-11-10 — S001, S002, S008, C001, C002, C004
- Checked: release date, platforms, price, director
- How: compared the press release, the store page and Gamewire Daily
- Found: date and platforms agree everywhere
- Result: S001 -> A; S008 -> A; S002 -> B; C001 -> 1; C002 -> 1; C004 -> 1

## 2026-11-10 — S005, S006, S007, C003
- Checked: the PS5 rumor
- How: read the three reports
- Found: three sites report a PS5 version in 2028
- Result: S005 -> D; S006 -> C; S007 -> D; C003 -> 1
"""


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = sys.argv[1]
    subprocess.run([sys.executable, os.path.join(HERE, "make_lantern_tide.py"), out], check=True, capture_output=True)
    index = os.path.join(out, "sources.md")
    with open(index, encoding="utf-8") as f:
        s = f.read()
    for sid, (rating, origin) in RATED.items():
        s = re.sub(r"(## " + sid + r" [\s\S]*?)- Rating: \n- Origin: \n",
                   lambda m: f"{m.group(1)}- Rating: {rating}\n- Origin: {origin}\n", s, count=1)
    with open(index, "w", encoding="utf-8") as f:
        f.write(s)
    with open(os.path.join(out, "claims.md"), "w", encoding="utf-8") as f:
        f.write(CLAIMS)
    with open(os.path.join(out, "factcheck-log.md"), "w", encoding="utf-8") as f:
        f.write(LOG)
    state_path = os.path.join(out, "STATE.md")
    with open(state_path, encoding="utf-8") as f:
        state = f.read()
    state = (state.replace("- Phase: collected", "- Phase: assessing (Q1-Q2 assessed, Q3 in progress)")
                  .replace("- User language: English", "- User language: українська")
                  .replace("- Reads: en, ja, uk", "- Reads: uk, ru, en")
                  .replace("- Quotes: “”", "- Quotes: «»")
                  .replace("- Plan approved as is. Sources are collected; next: assess, then write the article.",
                           "- Plan approved as is.\n- 2026-11-10: the user asked NOT to mention the budget in the "
                           "article (they cover it in a separate piece).")
                  .replace("- Sources S001-S011 saved and indexed (Rating and Origin not filled yet)",
                           "- Sources S001-S011 saved; S001, S002, S005-S008 rated; claims C001-C004 written")
                  .replace("- Assess (claims, ratings, origins, log), then draft and final.md",
                           "- Rate S003, S004, S009-S011; finish claims for Q2-Q3; report and evidence review; then "
                           "draft (in Ukrainian) and final.md"))
    with open(state_path, "w", encoding="utf-8") as f:
        f.write(state)
    print(f"built {out} (half-assessed, with planted mistakes)")


if __name__ == "__main__":
    main()
