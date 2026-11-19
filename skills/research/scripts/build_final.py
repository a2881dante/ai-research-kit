#!/usr/bin/env python3
"""Build final.md (clean copy for publishing) from draft.md. Never edit final.md by hand.

  build_final.py <research_dir> [-o OUT] [--quotes «»]

- [C003] / [C001, C007] / [S012] -> a footnote listing the supporting sources
  (title, URL, archive link) taken from claims.md and sources.md.
- S010 `original` — «translation» (перевод) -> «translation» in the text, original in the footnote.
- S010 `original` (no translation) -> the quote in the text's quotation marks, with a footnote.
- HTML comments and the working "## Sources" section are dropped.
Identical footnotes share one number. Exit 1 on unknown IDs (run check_quotes.py first).
"""
import argparse
import os
import re
import sys

from research_files import parse_claims, parse_sources

# One pattern, so footnotes are numbered in reading order: a quote or a [C001, S002] reference.
TOKEN = re.compile(r"\b(?P<sid>S\d{3,}):?\s*`(?P<orig>[^`\n]+)`"
                   r"(?:\s*[—–-]\s*(?P<tr>«[^»\n]*»|“[^”\n]*”|„[^“\n]*“|\"[^\"\n]*\"|「[^」\n]*」)(?:\s*\([^)\n]*\))?)?"
                   r"|\s?\[(?P<refs>[CS]\d{3,}(?:\s*[,;]\s*[CS]\d{3,})*)\]")
LABELS = {"ru": ("архив", "Оригинал"), "uk": ("архів", "Оригінал"), "en": ("archive", "Original")}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def language(state_text):
    m = re.search(r"^- User language:\s*(\S+)", state_text, re.M)
    lang = (m.group(1) if m else "").lower()
    if lang.startswith(("укр", "uk")):
        return "uk"
    if lang.startswith(("рус", "ru")):
        return "ru"
    return "en"


def build(draft, sources, claims, lang, quotes):
    archive_word, original_word = LABELS[lang]
    notes, order, errors = {}, [], []

    def cite(sid):
        if sid not in sources:
            errors.append(f"unknown source {sid}")
            return sid
        title, url, arch = (sources[sid][k] for k in ("title", "url", "archive"))
        return " — ".join(p for p in (title, url) if p) + (f" ({archive_word}: {arch})" if arch else "")

    def note(text):
        if text not in notes:
            order.append(text)
            notes[text] = len(order)
        return f"[^{notes[text]}]"

    def quote_sub(m):
        sid, original, translation = m.group("sid", "orig", "tr")
        if translation:
            return translation + note(f"{original_word}: {quotes[0]}{original}{quotes[1]} — {cite(sid)}")
        return f"{quotes[0]}{original}{quotes[1]}" + note(cite(sid))

    def ref_sub(m):
        sids = []
        for rid in re.split(r"\s*[,;]\s*", m.group("refs")):
            if rid.startswith("S"):
                sids.append(rid)
            elif rid not in claims:
                errors.append(f"unknown claim {rid}")
            elif not claims[rid]["supports"]:
                errors.append(f"claim {rid} has no Supports")
            else:
                sids += [sid for sid, _ in claims[rid]["supports"]]
        sids = list(dict.fromkeys(sids))
        return note("; ".join(cite(s) for s in sids)) if sids else ""

    text = re.sub(r"<!--.*?-->", "", draft, flags=re.S)
    text = re.split(r"^## (?:Sources|Источники|Джерела)\s*$", text, maxsplit=1, flags=re.M)[0]
    text = TOKEN.sub(lambda m: ref_sub(m) if m.group("refs") else quote_sub(m), text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    if order:
        text += "\n" + "".join(f"[^{i}]: {t}\n" for i, t in enumerate(order, 1))
    return text, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("research_dir")
    ap.add_argument("-o", "--out", help="output file (default: <research_dir>/final.md)")
    ap.add_argument("--quotes", help="opening and closing quotation marks, e.g. «» or “”")
    a = ap.parse_args()

    rd = a.research_dir
    state = os.path.join(rd, "STATE.md")
    lang = language(read(state) if os.path.exists(state) else "")
    quotes = a.quotes or ("«»" if lang in ("ru", "uk") else "“”")
    if len(quotes) != 2:
        sys.exit("--quotes takes exactly two characters, e.g. «»")
    claims = parse_claims(read(os.path.join(rd, "claims.md"))) if os.path.exists(os.path.join(rd, "claims.md")) else {}
    text, errors = build(read(os.path.join(rd, "draft.md")), parse_sources(read(os.path.join(rd, "sources.md"))),
                         claims, lang, quotes)
    if errors:
        print("\n".join(sorted(set(errors))), file=sys.stderr)
        sys.exit(1)
    out = a.out or os.path.join(rd, "final.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {out} ({text.count(chr(10) + '[^')} footnotes)")


if __name__ == "__main__":
    main()
