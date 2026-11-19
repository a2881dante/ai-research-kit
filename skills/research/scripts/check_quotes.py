#!/usr/bin/env python3
"""Check quotes and references in a research folder.

  check_quotes.py <research_dir> [file ...]
      Files are relative to research_dir. Default: sources.md claims.md draft.md (those that
      exist) and every sources/S*/translation.*.md.

- Every quote must appear verbatim in its source's original.md.
  Syntax: S012 `exact text`  or  S012: `exact text`.
  A bare `text` under a "## S012 ..." heading belongs to S012 (key phrases in sources.md).
  Whitespace differences are ignored; everything else must match exactly. A cut marked
  [...] or […] is allowed: every part must be present, in order.
- Every S012 / C007 mentioned must exist (a sources/S012 folder, a "## C007" heading in claims.md).
- In a translation file, every "> " line (a paragraph of the original) must appear verbatim
  in that source's original.md, so the bilingual view shows the real original.
- For draft files, lists cited claims with credibility 3-6, so you can check they read as
  rumor or doubt, not fact.
Exit 0 if no problems, 1 otherwise.
"""
import glob
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


def found(quote, text):
    """Quote in text; a cut marked [...] or […] needs every part present, in order."""
    pos = 0
    for part in re.split(r"\s*\[(?:\.\.\.|…)\]\s*", quote):
        part = " ".join(part.split())
        if part:
            pos = text.find(part, pos)
            if pos < 0:
                return False
            pos += len(part)
    return True


def claim_credibility(research_dir):
    """{claim id: credibility digit or ''} from claims.md."""
    claims, current = {}, None
    path = os.path.join(research_dir, "claims.md")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"## (C\d{3,})\b", line)
                if m:
                    current = m.group(1)
                    claims[current] = ""
                elif current and line.startswith("- Credibility:"):
                    d = re.search(r"\d", line)
                    claims[current] = d.group(0) if d else ""
    return claims


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rd = sys.argv[1]
    files = sys.argv[2:] or (
        [f for f in ("sources.md", "claims.md", "draft.md") if os.path.exists(os.path.join(rd, f))]
        + sorted(os.path.relpath(p, rd) for p in glob.glob(os.path.join(rd, "sources", "S*", "translation.*.md"))))
    claims = claim_credibility(rd)
    cache, checked, problems = {}, 0, 0
    weak = {}  # claim id -> ["draft.md:12", ...]

    def problem(msg):
        nonlocal problems
        print(msg)
        problems += 1

    for name in files:
        path = os.path.join(rd, name)
        section = None
        is_draft = os.path.basename(name).startswith("draft")
        tr = re.match(r"sources/(S\d{3,})/translation\.[\w-]+\.md$", name.replace(os.sep, "/"))
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                where = f"{name}:{ln}"
                if tr:  # translation file: only the quoted original paragraphs are checked
                    text = line[1:].strip() if line.startswith(">") else ""
                    if text:
                        checked += 1
                        src = load(rd, tr.group(1), cache)
                        if src is None or " ".join(text.split()) not in src[0]:
                            problem(f"{where}: original paragraph not found in {tr.group(1)}: {text[:60]}")
                    continue
                if line.startswith("## "):
                    m = re.match(r"## (S\d{3,})\b", line)
                    section = m and m.group(1)
                quoted = set()
                for sid, quote in QUOTE.findall(line):
                    sid = sid or section
                    if not sid:
                        continue
                    checked += 1
                    quoted.add(sid)
                    src = load(rd, sid, cache)
                    if src is None:
                        problem(f"{where}: {sid} has no original.md: `{quote}`")
                    elif not found(quote, src[0]):
                        problem(f"{where}: NOT FOUND in {sid}: `{quote}`")
                    elif src[1] == "model-fetch":
                        print(f"{where}: WARNING {sid} is model-fetch (may not be verbatim): `{quote}`")
                for sid in set(re.findall(r"\b(S\d{3,})\b", line)) - quoted:
                    if not os.path.isdir(os.path.join(rd, "sources", sid)):
                        problem(f"{where}: unknown source {sid}")
                for cid in sorted(set(re.findall(r"\b(C\d{3,})\b", line))):
                    if cid not in claims:
                        problem(f"{where}: unknown claim {cid}")
                    elif is_draft and claims[cid] in ("3", "4", "5", "6"):
                        weak.setdefault(cid, []).append(where)
    if weak:
        print("Cited claims with credibility 3-6 (check they read as rumor or doubt, not fact):")
        for cid, places in sorted(weak.items()):
            print(f"  {cid} ({claims[cid]}): {', '.join(places)}")
    print(f"{checked} quotes checked, {problems} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
