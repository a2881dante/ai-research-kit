#!/usr/bin/env python3
"""Check that every quote attributed to a source appears verbatim in its original.md.

  check_quotes.py <research_dir> [file ...]
      Files are relative to research_dir. Default: sources.md claims.md draft.md (those that exist).

Quote syntax: S012 `exact text`  or  S012: `exact text`
A bare `text` under a "## S012 ..." heading belongs to S012 (key phrases in sources.md).
Whitespace differences are ignored; everything else must match exactly.
Exit 0 if every quote was found, 1 otherwise.
"""
import os
import re
import sys

QUOTE = re.compile(r"(?:\b(S\d{3,})\b:?\s*)?`([^`\n]+)`")


def load(research_dir, sid, cache):
    """(whitespace-collapsed text, capture) of a source, or None if it has no original.md."""
    if sid not in cache:
        path = os.path.join(research_dir, "sources", sid, "original.md")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            m = re.search(r'^capture: "(.*)"$', text, re.M)
            cache[sid] = (" ".join(text.split()), m.group(1) if m else "")
        else:
            cache[sid] = None
    return cache[sid]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rd = sys.argv[1]
    files = sys.argv[2:] or [f for f in ("sources.md", "claims.md", "draft.md")
                             if os.path.exists(os.path.join(rd, f))]
    cache, checked, problems = {}, 0, 0
    for name in files:
        path = os.path.join(rd, name)
        section = None
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                if line.startswith("## "):
                    m = re.match(r"## (S\d{3,})\b", line)
                    section = m and m.group(1)
                for sid, quote in QUOTE.findall(line):
                    sid = sid or section
                    if not sid:
                        continue
                    checked += 1
                    src = load(rd, sid, cache)
                    if src is None:
                        print(f"{name}:{ln}: {sid} has no original.md: `{quote}`")
                        problems += 1
                    elif " ".join(quote.split()) not in src[0]:
                        print(f"{name}:{ln}: NOT FOUND in {sid}: `{quote}`")
                        problems += 1
                    elif src[1] == "model-fetch":
                        print(f"{name}:{ln}: WARNING {sid} is model-fetch (may not be verbatim): `{quote}`")
    print(f"{checked} quotes checked, {problems} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
