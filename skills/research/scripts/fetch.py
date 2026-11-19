#!/usr/bin/env python3
"""Save a web source verbatim into a research folder and register it in sources.md.

  fetch.py <research_dir> <url>
      Download the page, extract its text, keep the raw file, look up a Wayback snapshot.
  fetch.py <research_dir> <url> --text-file FILE --capture model-fetch|user-paste|<tool>
      Register text obtained some other way (fallback, or another tool/integration).

Exit codes: 0 saved, 1 download failed, 3 already saved (prints the ID),
4 too little text extracted (nothing saved; see --min-chars).
Stdlib only.
"""
import argparse
import datetime
import gzip
import json
import mimetypes
import os
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
MAX_BYTES = 30 * 1024 * 1024
SKIP = {"script", "style", "noscript", "template", "svg"}
BLOCK = {"p", "div", "section", "article", "main", "header", "footer", "aside", "nav",
         "blockquote", "pre", "ul", "ol", "dl", "dt", "dd", "table", "tr", "form",
         "figure", "figcaption", "hr", "address", "details", "summary",
         "h1", "h2", "h3", "h4", "h5", "h6"}
# Japanese sites say Shift_JIS but use the Windows superset (①, ㈱ ...).
CHARSET_ALIASES = {"shift_jis": "cp932", "shift-jis": "cp932", "sjis": "cp932",
                   "x-sjis": "cp932", "windows-31j": "cp932"}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.title, self.lang = [], "", ""
        self.skip = 0
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "html":
            self.lang = dict(attrs).get("lang") or ""
        if tag in SKIP:
            self.skip += 1
        elif self.skip:
            return
        elif tag == "title":
            self.in_title = True
        elif tag == "br":
            self.out.append("\n")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag in BLOCK:
            self.out.append("\n\n" if tag == "p" else "\n")

    def handle_startendtag(self, tag, attrs):
        if tag not in SKIP:  # <svg/> must not open a skip region
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag == "title":
            self.in_title = False
        elif tag in BLOCK and not self.skip:
            self.out.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_title:
            self.title += data
        else:
            self.out.append(re.sub(r"\s+", " ", data))

    def text(self):
        # ponytail: <pre> indentation is flattened; raw.html keeps the exact original.
        lines = (line.strip() for line in "".join(self.out).split("\n"))
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def to_uri(url):
    """Percent-encode non-ASCII paths (Cyrillic, Japanese) and IDN hosts so urllib accepts them."""
    p = urllib.parse.urlsplit(url)
    netloc = p.netloc
    if not netloc.isascii():
        host, _, port = netloc.partition(":")
        netloc = host.encode("idna").decode() + (":" + port if port else "")
    safe = "/?#[]@!$&'()*+,;=%:~"
    return urllib.parse.urlunsplit((p.scheme, netloc, urllib.parse.quote(p.path, safe=safe),
                                    urllib.parse.quote(p.query, safe=safe), ""))


def decode(body, header_charset):
    """Header charset, then <meta charset>, then UTF-8. Returns (text, charset used)."""
    m = re.search(rb"""<meta[^>]+charset=["']?([\w.:-]+)""", body[:8192], re.I)
    for cs in (header_charset, m and m.group(1).decode("ascii", "ignore")):
        if cs:
            cs = CHARSET_ALIASES.get(cs.lower(), cs)
            try:
                return body.decode(cs), cs
            except (LookupError, UnicodeDecodeError):
                pass
    try:
        return body.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return body.decode("utf-8", "replace"), "utf-8 (with replaced bytes)"


def download(url):
    req = urllib.request.Request(to_uri(url), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read(MAX_BYTES + 1)
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return body[:MAX_BYTES], r.headers, r.url, len(body) > MAX_BYTES


def archive(url, save):
    """Find an existing Wayback snapshot. With save=True first ask Wayback to make a new,
    public one: that publishes the URL, so it's opt-in."""
    uri = to_uri(url)
    if save:
        try:
            req = urllib.request.Request("https://web.archive.org/save/" + uri, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                loc = r.headers.get("Content-Location")
                if loc:
                    return "https://web.archive.org" + loc
                if "/web/" in r.url:
                    return r.url
        except Exception:
            pass
    try:
        api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(uri, safe="")
        with urllib.request.urlopen(api, timeout=30) as r:
            snap = json.load(r).get("archived_snapshots", {}).get("closest", {})
    except Exception as e:
        return f"unknown (lookup failed: {e})"
    if snap.get("available"):
        return snap["url"] + " (existing snapshot, may differ from accessed version)"
    return "none"


def next_id_dir(sources_dir):
    os.makedirs(sources_dir, exist_ok=True)
    nums = [int(d[1:]) for d in os.listdir(sources_dir) if re.fullmatch(r"S\d+", d)]
    n = max(nums, default=0) + 1
    while True:  # mkdir is atomic, so parallel agents never get the same ID
        sid = f"S{n:03d}"
        try:
            os.mkdir(os.path.join(sources_dir, sid))
            return sid
        except FileExistsError:
            n += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("research_dir")
    ap.add_argument("url")
    ap.add_argument("--archive", action="store_true",
                    help="ask Wayback to make a new PUBLIC snapshot (only when the user wants it)")
    ap.add_argument("--no-archive", action="store_true", help="don't contact Wayback at all")
    ap.add_argument("--text-file", help="register this UTF-8 text instead of downloading")
    ap.add_argument("--capture", default="model-fetch", help="how --text-file was obtained")
    ap.add_argument("--title", default="")
    ap.add_argument("--min-chars", type=int, default=300,
                    help="refuse pages with less extracted text (JS-only/blocked pages); 0 to allow")
    a = ap.parse_args()

    if not re.match(r"https?://", a.url):
        sys.exit("url must start with http:// or https://")
    index = os.path.join(a.research_dir, "sources.md")
    existing = open(index, encoding="utf-8").read() if os.path.exists(index) else ""
    known = {u: sid for sid, u in re.findall(r"^## (S\d+).*\n- URL: (.*)$", existing, re.M)}
    if a.url in known:
        print(f"{known[a.url]} already saved: {a.url}")
        sys.exit(3)

    meta = {"url": a.url, "title": a.title, "lang": "",
            "accessed": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    raw = None  # (bytes, filename)
    if a.text_file:
        text = open(a.text_file, encoding="utf-8").read()
        meta["capture"] = a.capture
    else:
        try:
            body, headers, final_url, truncated = download(a.url)
        except Exception as e:
            print(f"FAILED to download {a.url}: {e}", file=sys.stderr)
            sys.exit(1)
        meta["capture"] = "script"
        if final_url != to_uri(a.url):
            meta["final_url"] = final_url
        if truncated:
            meta["truncated"] = f"first {MAX_BYTES} bytes only"
        ctype = headers.get_content_type()
        if ctype in ("text/html", "application/xhtml+xml"):
            decoded, meta["charset"] = decode(body, headers.get_content_charset())
            p = TextExtractor()
            p.feed(decoded)
            p.close()
            text, meta["lang"] = p.text(), p.lang
            meta["title"] = a.title or " ".join(p.title.split())
            raw = (body, "raw.html")
        elif ctype.startswith("text/") or ctype.endswith(("json", "xml")):
            text, meta["charset"] = decode(body, headers.get_content_charset())
        else:
            name = "original" + (mimetypes.guess_extension(ctype) or ".bin")
            text = f"(binary {ctype}: text not extracted, see {name})\n"
            raw = (body, name)
            a.min_chars = 0
        if len(text) < a.min_chars:
            print(f"Only {len(text)} chars extracted from {a.url}; nothing saved. The page is probably "
                  f"JavaScript-rendered, blocked or a captcha. Use the fallback (--text-file), or "
                  f"--min-chars 0 if the page is legitimately short.", file=sys.stderr)
            sys.exit(4)

    meta["archive"] = "skipped" if a.no_archive else archive(a.url, a.archive)
    sid = next_id_dir(os.path.join(a.research_dir, "sources"))
    folder = os.path.join(a.research_dir, "sources", sid)
    if raw:
        with open(os.path.join(folder, raw[1]), "wb") as f:
            f.write(raw[0])
    front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in {"id": sid, **meta}.items() if v)
    with open(os.path.join(folder, "original.md"), "w", encoding="utf-8") as f:
        f.write(f"---\n{front}\n---\n\n{text}")

    entry = (f"## {sid} — {meta['title'] or a.url}\n- URL: {a.url}\n- Archive: {meta['archive']}\n"
             f"- Accessed: {meta['accessed'][:10]}\n- Language: {meta['lang']}\n- Capture: {meta['capture']}\n"
             f"- Type: \n- Subquestions: \n- Key phrases: \n- Notes: \n\n")
    with open(index, "a", encoding="utf-8") as f:
        f.write(("# Sources\n\n" if not existing else "") + entry)
    print(f"{sid} saved: {folder}/original.md ({len(text)} chars, lang={meta['lang'] or '?'}, "
          f"archive={meta['archive']})")


if __name__ == "__main__":
    main()
