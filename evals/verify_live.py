#!/usr/bin/env python3
"""Check live-research articles against the web: do the cited URLs open, and are the quoted
words actually on the cited pages? Runs outside the eval sandbox, after the eval.

  python3 evals/verify_live.py <aggregate-result.json> [--case shenmue-live] [--out report.json]

Takes each run's final.md from the eval result (an LLM grader that focuses on final.md stores
the file's text), so the sealed workspaces don't need to be opened.

Per arm it reports:
  URLs: opened / broken (404, DNS, ...) / blocked (403, 429, Cloudflare: can't tell)
  Quotes (5+ words in “”, «», "" quotes): found on a cited page / not found on any of the
  cited pages that opened / unverifiable (no cited page opened)
Translated quotes can't match the page: a Cyrillic quote that isn't on any cited page is counted
as a translation and listed for a manual check against its original (in a plugin article the
original is in the footnote, and is checked as a quote of its own).
"""
import argparse
import json
import os
import re
import sys
import urllib.error

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "research", "scripts")
sys.path.insert(0, SCRIPTS)
from check_quotes import norm  # noqa: E402
from fetch import TextExtractor, decode, download  # noqa: E402

URL = re.compile(r"https?://(?:[^\s()<>\"'»”\]]|\([^\s()]*\))+")  # keeps balanced (...) as in Wikipedia URLs
CYRILLIC = re.compile(r"[а-яёіїєґ]", re.I)
QUOTE = re.compile(r"“([^”\n]+)”|«([^»\n]+)»|\"([^\"\n]+)\"")


def page_text(url, cache):
    """(status, normalized text): status is ok, broken or blocked."""
    if url not in cache:
        try:
            try:
                body, headers, _, _ = download(url)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if isinstance(e, urllib.error.HTTPError):
                    raise
                body, headers, _, _ = download(url)  # one retry: Wayback and some sites time out now and then
            if headers.get_content_type() in ("text/html", "application/xhtml+xml"):
                html, _ = decode(body, headers.get_content_charset())
                p = TextExtractor()
                p.feed(html)
                text = p.title + "\n" + p.text()  # quoted article titles are checked against the page title too
            else:
                text, _ = decode(body, headers.get_content_charset())
            cache[url] = ("ok", norm(text).casefold())
        except urllib.error.HTTPError as e:
            cache[url] = ("blocked" if e.code in (401, 403, 429, 451, 503) else "broken", "")
        except Exception:
            cache[url] = ("broken", "")
    return cache[url]


def on_page(quote, text):
    """Quote in page text, ignoring markdown emphasis and edge punctuation; "…" marks a cut."""
    quote = re.sub(r"[*_`]", "", quote)
    pos = 0
    for part in re.split(r"\s*(?:…|\.\.\.|\[\.\.\.\]|\[…\])\s*", quote):
        part = norm(part.strip(" ,.;:!?")).casefold()
        if part:
            pos = text.find(part, pos)
            if pos < 0:
                return False
            pos += len(part)
    return True


def check(article, cache):
    urls = sorted({u.rstrip(".,;") for u in URL.findall(article)})
    pages = {u: page_text(u, cache) for u in urls}
    opened = [t for s, t in pages.values() if s == "ok"]
    quotes = [next(g for g in m if g) for m in QUOTE.findall(article)]
    quotes = [q for q in quotes if len(q.split()) >= 5 or len(q) >= 20 and not q.isascii()]
    found, missing, translated, unverifiable = [], [], [], []
    for q in quotes:
        if not opened:
            unverifiable.append(q)
        elif any(on_page(q, t) for t in opened):
            found.append(q)
        elif CYRILLIC.search(q):
            translated.append(q)
        else:
            missing.append(q)
    status = [s for s, _ in pages.values()]
    return {"urls": len(urls), "opened": status.count("ok"), "broken": status.count("broken"),
            "blocked": status.count("blocked"), "broken_urls": [u for u, (s, _) in pages.items() if s == "broken"],
            "quotes": len(quotes), "found": len(found), "missing": missing, "translated": translated,
            "unverifiable": len(unverifiable)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("result")
    ap.add_argument("--case", default="shenmue-live")
    ap.add_argument("--grader", default="budget-disputed-and-attributed",
                    help="an LLM grader that focuses on final.md (its evidence is the article text)")
    ap.add_argument("--out")
    a = ap.parse_args()
    data = json.load(open(a.result, encoding="utf-8"))
    case = next(c for c in data["cases"] if c["name"] == a.case)
    cache, report = {}, {}
    for arm, runs in case["arms"].items():
        report[arm] = []
        for r in runs:
            article = next((g.get("evidence") or "" for g in r["graders"] if g["name"] == a.grader), "")
            report[arm].append(check(article, cache) if article else {"error": "no final.md text in the result"})
    for arm, runs in report.items():
        ok = [r for r in runs if "error" not in r]
        tot = lambda k: sum(r[k] for r in ok)  # noqa: E731
        missing = sum(len(r["missing"]) for r in ok)
        translated = sum(len(r["translated"]) for r in ok)
        print(f"{arm}: {len(ok)} articles | URLs {tot('urls')}: opened {tot('opened')}, broken {tot('broken')}, "
              f"blocked {tot('blocked')} | quotes {tot('quotes')}: found {tot('found')}, not on cited pages "
              f"{missing}, translations to check {translated}, unverifiable {tot('unverifiable')}")
        for r in ok:
            for q in r["missing"]:
                print(f"    not found: “{q[:120]}”")
            for q in r["translated"]:
                print(f"    translation: “{q[:120]}”")
            for u in r["broken_urls"]:
                print(f"    broken URL: {u}")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
