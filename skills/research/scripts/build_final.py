#!/usr/bin/env python3
"""Build final.md (clean copy for publishing) from draft.md. Never edit final.md by hand.

  build_final.py <research_dir> [-o OUT] [--quotes «»] [--style footnotes|numbered|author-date]

- [C003] / [C001, C007] / [S012] -> a citation of the supporting sources (from claims.md and
  sources.md) in the chosen style:
    footnotes    a footnote with title, URL and archive link (default)
    numbered     [1, 3] in the text and a numbered source list
    author-date  (Author, 2026) in the text and a source list sorted by author
- S010 `original` — «translation» (перевод) -> «translation» in the text, original in a footnote.
- S010 `original` (no translation) -> the quote in the text's quotation marks, cited.
- [CK] (common knowledge) marks, HTML comments and the working "## Sources" section are dropped.
Style, quotation marks and language come from STATE.md (Citation style, Quotes, User language)
unless given as options. Exit 1 on unknown IDs (run check_quotes.py first).
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
LABELS = {  # archive, original, sources heading, no date
    "ru": ("архив", "Оригинал", "Источники", "б. г."),
    "uk": ("архів", "Оригінал", "Джерела", "б. р."),
    "en": ("archive", "Original", "Sources", "n.d."),
}
STYLES = ("footnotes", "numbered", "author-date")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def setting(state_text, name):
    m = re.search(r"^- " + re.escape(name) + r":[ \t]*(.*)$", state_text, re.M)
    return re.sub(r"<!--.*?-->|\(.*?\)", "", m.group(1)).strip() if m else ""


def language(state_text):
    lang = setting(state_text, "User language").lower()
    if lang.startswith(("укр", "uk")):
        return "uk"
    if lang.startswith(("рус", "ru")):
        return "ru"
    return "en"


def build(draft, sources, claims, lang, quotes, style="footnotes"):
    archive_word, original_word, heading, no_date = LABELS[lang]
    notes, order, errors, used = {}, [], [], []

    def cite(sid):
        if sid not in sources:
            errors.append(f"unknown source {sid}")
            return sid
        s = sources[sid]
        return " — ".join(p for p in (s["title"], s["url"]) if p) + (f" ({archive_word}: {s['archive']})" if s["archive"] else "")

    def author(sid):
        s = sources.get(sid, {})
        a = re.sub(r"\(.*?\)", "", s.get("author", "")).strip()
        if not a or a.lower() in ("unknown", "неизвестно", "невідомо", "n/a", "-"):
            a = s.get("title", sid)[:50]
        return a

    def year(sid):
        m = re.search(r"\b(\d{4})\b", sources.get(sid, {}).get("published", ""))
        return m.group(1) if m else no_date

    def note(text):
        if text not in notes:
            order.append(text)
            notes[text] = len(order)
        return f"[^{notes[text]}]"

    def mark(sids):
        """Citation of these sources in the chosen style."""
        used.extend(s for s in sids if s not in used)
        if style == "numbered":
            return " [" + ", ".join(str(used.index(s) + 1) for s in sids) + "]"
        if style == "author-date":
            return " (" + "; ".join(f"{author(s)}, {year(s)}" for s in sids) + ")"
        return note("; ".join(cite(s) for s in sids))

    def quote_sub(m):
        sid, original, translation = m.group("sid", "orig", "tr")
        original = f"{quotes[0]}{original}{quotes[1]}"
        if not translation:
            return original + mark([sid])
        if style == "footnotes":
            return translation + note(f"{original_word}: {original} — {cite(sid)}")
        return translation + mark([sid]) + note(f"{original_word}: {original}")

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
        return mark(sids) if sids else ""

    text = re.sub(r"<!--.*?-->", "", draft, flags=re.S)
    text = re.sub(r"\s?\[CK\]", "", text)  # common-knowledge marks get no citation
    text = re.split(r"^## (?:Sources|Источники|Джерела)\s*$", text, maxsplit=1, flags=re.M)[0]
    text = TOKEN.sub(lambda m: ref_sub(m) if m.group("refs") else quote_sub(m), text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    if style == "numbered" and used:
        text += f"\n## {heading}\n\n" + "".join(f"{i}. {cite(s)}\n" for i, s in enumerate(used, 1))
    elif style == "author-date" and used:
        # ponytail: generic author-date list, not strict APA/Chicago; polish by hand if a journal demands it
        items = sorted(used, key=lambda s: (author(s).lower(), year(s)))
        text += f"\n## {heading}\n\n" + "".join(f"- {author(s)} ({year(s)}). {cite(s)}\n" for s in items)
    if order:
        text += "\n" + "".join(f"[^{i}]: {t}\n" for i, t in enumerate(order, 1))
    return text, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("research_dir")
    ap.add_argument("-o", "--out", help="output file (default: <research_dir>/final.md)")
    ap.add_argument("--quotes", help="opening and closing quotation marks, e.g. «» or “”")
    ap.add_argument("--style", choices=STYLES, help="citation style (default: from STATE.md, else footnotes)")
    a = ap.parse_args()

    rd = a.research_dir
    state_path = os.path.join(rd, "STATE.md")
    state = read(state_path) if os.path.exists(state_path) else ""
    lang = language(state)
    quotes = a.quotes or setting(state, "Quotes") or ("«»" if lang in ("ru", "uk") else "“”")
    if len(quotes) != 2:
        sys.exit("quotation marks must be exactly two characters, e.g. «»")
    style = a.style or setting(state, "Citation style").lower() or "footnotes"
    if style not in STYLES:
        sys.exit(f"unknown citation style {style!r}; use one of {', '.join(STYLES)}")
    claims_path = os.path.join(rd, "claims.md")
    claims = parse_claims(read(claims_path)) if os.path.exists(claims_path) else {}
    text, errors = build(read(os.path.join(rd, "draft.md")), parse_sources(read(os.path.join(rd, "sources.md"))),
                         claims, lang, quotes, style)
    if errors:
        print("\n".join(sorted(set(errors))), file=sys.stderr)
        sys.exit(1)
    out = a.out or os.path.join(rd, "final.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {out} ({style}, {text.count(chr(10) + '[^')} footnotes)")


if __name__ == "__main__":
    main()
