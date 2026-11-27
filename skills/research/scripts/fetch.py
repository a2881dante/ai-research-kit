#!/usr/bin/env python3
"""Save a web source verbatim into a research folder and register it in sources.md.

  fetch.py <research_dir> <url>
      Download the page, extract its text, keep the raw file, look up a Wayback snapshot.
  fetch.py <research_dir> <url> --text-file FILE --capture model-fetch|user-paste|<tool>
      Register text obtained some other way (fallback, or another tool/integration).

Wikis (MediaWiki: Wikipedia, Fandom...): a page that refuses the download is read through the
wiki's own API, and an api.php?action=parse URL is saved under the page's own /wiki/ URL.

PDFs: text is extracted with [page N] markers if pdftotext (poppler) or pypdf is installed.

Exit codes: 0 saved, 1 download failed, 3 already saved (prints the ID; URLs are compared
ignoring scheme, www/m. prefixes, tracking parameters and the like), 4 too little text
extracted (nothing saved; see --min-chars), 5 PDF but no PDF text tool installed.
Stdlib only (PDF text needs one of the tools above).
"""
import argparse
import datetime
import gzip
import hashlib
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
# Wikimedia and some others refuse a browser-like agent from a script but accept an honest one
BOT_UA = "research-kit (+https://github.com/a2881dante/ai-research-kit) python-urllib"
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


def pdf_text(body):
    """(text with [page N] markers, tool name) via pdftotext (poppler) or pypdf, whichever is
    installed; (None, None) if neither is."""
    pages, tool = None, None
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-", "-"], input=body, capture_output=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {r.stderr.decode('utf-8', 'replace').strip()}")
        pages, tool = r.stdout.decode("utf-8", "replace").split("\f"), "pdftotext"
    else:
        try:
            import pypdf
        except ImportError:
            return None, None
        pages, tool = [p.extract_text() or "" for p in pypdf.PdfReader(io.BytesIO(body)).pages], "pypdf"
    pages = [p.strip() for p in pages]
    while pages and not pages[-1]:  # pdftotext ends with a form feed
        pages.pop()
    # ponytail: words hyphenated across lines stay split; quote them as they appear in original.md
    return "".join(f"[page {i}]\n\n{p}\n\n" for i, p in enumerate(pages, 1)), tool


TRACKING = re.compile(r"utm_\w+|fbclid|gclid|yclid|dclid|msclkid|mc_cid|mc_eid|igshid|si|ref_src|ref_url")


def wiki_title(url):
    """(scheme://host, page title) for a MediaWiki page or api.php?action=parse URL, else None."""
    p = urllib.parse.urlsplit(url)
    q = dict(urllib.parse.parse_qsl(p.query))
    if p.path.endswith("/api.php") and q.get("action") == "parse" and q.get("page"):
        title = q["page"]
    elif p.path.startswith("/wiki/") and len(p.path) > 6 and not q:
        title = urllib.parse.unquote(p.path[6:])
    else:
        return None
    return f"{p.scheme}://{p.netloc}", title.replace(" ", "_")


def wiki_page_url(url):
    """The page's own URL for an api.php?action=parse URL; other URLs unchanged."""
    w = wiki_title(url)
    return f"{w[0]}/wiki/{urllib.parse.quote(w[1], safe='/()_,:')}" if w and "api.php" in url else url


def wiki_api_download(url):
    """Read a MediaWiki page through its API (rendered HTML, redirects followed)."""
    base, title = wiki_title(url)
    err = None
    for api in ("/api.php", "/w/api.php"):  # Fandom, Wikipedia
        q = urllib.parse.urlencode({"action": "parse", "page": title, "prop": "text", "format": "json",
                                    "redirects": 1, "formatversion": 2})
        try:
            return download(f"{base}{api}?{q}", BOT_UA)
        except urllib.error.HTTPError as e:
            err = e
    raise err


def mediawiki_json(body):
    """(html or wikitext, is_html, title) from an action=parse JSON answer, or None."""
    try:
        parse = json.loads(body)["parse"]
    except (ValueError, KeyError, TypeError):
        return None
    for key, is_html in (("text", True), ("wikitext", False)):
        v = parse.get(key)
        if isinstance(v, dict):  # formatversion=1: {"*": ...}
            v = v.get("*")
        if isinstance(v, str):
            return v, is_html, parse.get("title", "")
    return None


def url_key(url):
    """What makes two URLs the same page, for duplicate detection: scheme, www./m./old./amp.
    prefixes, the en.m. mobile segment, case of the host, percent-encoding, trailing slash,
    fragment, tracking parameters and parameter order don't count."""
    p = urllib.parse.urlsplit(wiki_page_url(url.strip()))  # api.php?action=parse&page=X is the page X
    host = (p.hostname or "").lower()
    host = re.sub(r"^(?:www|m|mobile|old|amp)\.", "", host).replace(".m.", ".")
    if not host.isascii():
        host = host.encode("idna").decode()
    port = f":{p.port}" if p.port not in (None, 80, 443) else ""
    path = urllib.parse.unquote(p.path).rstrip("/") or "/"
    query = sorted((k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
                   if not TRACKING.fullmatch(k))
    return host + port + path + ("?" + urllib.parse.urlencode(query) if query else "")


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


def download(url, ua=UA):
    req = urllib.request.Request(to_uri(url), headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read(MAX_BYTES + 1)
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return body[:MAX_BYTES], r.headers, r.url, len(body) > MAX_BYTES


def wayback_lookup(url):
    """Closest existing Wayback snapshot: returns (snapshot_url, timestamp) or (None, None)."""
    api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(to_uri(url), safe="")
    with urllib.request.urlopen(api, timeout=30) as r:
        snap = json.load(r).get("archived_snapshots", {}).get("closest", {})
    return (snap["url"], snap.get("timestamp")) if snap.get("available") else (None, None)


def archive(url, save):
    """Find an existing Wayback snapshot. With save=True first ask Wayback to make a new,
    public one: that publishes the URL, so it's opt-in."""
    if save:
        try:
            req = urllib.request.Request("https://web.archive.org/save/" + to_uri(url), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                loc = r.headers.get("Content-Location")
                if loc:
                    return "https://web.archive.org" + loc
                if "/web/" in r.url:
                    return r.url
        except Exception:
            pass
    try:
        snap_url, _ = wayback_lookup(url)
    except Exception as e:
        return f"unknown (lookup failed: {e})"
    return snap_url + " (existing snapshot, may differ from accessed version)" if snap_url else "none"


def download_via_wayback(url):
    """Fallback for a failed live fetch: download the closest snapshot, toolbar-free via the
    id_ modifier. Returns (body, headers, snapshot_url, truncated), or None if no snapshot."""
    snap_url, ts = wayback_lookup(url)
    if not snap_url:
        return None
    raw = f"https://web.archive.org/web/{ts}id_/{to_uri(url)}" if ts else snap_url
    body, headers, _, truncated = download(raw)
    return body, headers, snap_url, truncated


def fetch_live(url):
    """Download; on 403/429 retry with an honest agent, then (for a wiki page) via the wiki's API."""
    try:
        return download(url)
    except urllib.error.HTTPError as e:
        if e.code not in (403, 429):
            raise
        try:
            return download(url, BOT_UA)
        except urllib.error.HTTPError as e2:
            if e2.code not in (403, 429) or not wiki_title(url) or "api.php" in url:
                raise
            return wiki_api_download(url)


class Lock:
    """Parallel agents: one at a time re-checks sources.md, takes an ID and appends its entry."""
    def __init__(self, research_dir):
        self.path = os.path.join(research_dir, ".fetch.lock")

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        for _ in range(600):
            try:
                os.mkdir(self.path)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > 120:  # left by a killed process
                        os.rmdir(self.path)
                except OSError:
                    pass
                time.sleep(0.1)
        raise SystemExit(f"{self.path} is held by another fetch.py for over a minute; remove it if none is running")

    def __exit__(self, *exc):
        os.rmdir(self.path)


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

    def stop_if_known(url):
        existing = open(index, encoding="utf-8").read() if os.path.exists(index) else ""
        known = {url_key(u): (sid, u) for sid, u in re.findall(r"^## (S\d+).*\n- URL: (.*)$", existing, re.M)}
        if url_key(url) in known:
            sid, saved = known[url_key(url)]
            print(f"{sid} already saved: {saved}" + (f" (same page as {url})" if saved != url else ""))
            sys.exit(3)
        return existing

    stop_if_known(a.url)
    page_url = wiki_page_url(a.url)  # an API address is saved under the page's own URL

    meta = {"url": page_url, "fetched_from": a.url if page_url != a.url else "", "title": a.title, "lang": "",
            "accessed": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    raw = None  # (bytes, filename)
    if a.text_file:
        text = open(a.text_file, encoding="utf-8").read()
        meta["capture"] = a.capture
    else:
        try:
            body, headers, final_url, truncated = fetch_live(a.url)
            meta["capture"] = "script"
            if "api.php" in final_url and "api.php" not in a.url:
                meta["fetched_from"] = final_url
            elif final_url != to_uri(a.url):
                meta["final_url"] = final_url
                stop_if_known(final_url)  # a redirect can land on a page that's already saved
        except Exception as e:
            fb = wb_err = None  # live fetch failed (403/DNS/timeout): fall back to a Wayback snapshot
            if not a.no_archive:
                try:
                    fb = download_via_wayback(page_url)
                except Exception as we:
                    wb_err = we  # surface it: a transient archive.org hiccup is worth a retry
            if not fb:
                extra = f"; Wayback fallback also failed: {wb_err}" if wb_err else "; no Wayback snapshot"
                print(f"FAILED to download {a.url}: {e}{extra}", file=sys.stderr)
                sys.exit(1)
            body, headers, final_url, truncated = fb
            meta["capture"] = "wayback"
            meta["final_url"] = final_url
            meta["live_fetch_error"] = str(e)
            meta["archive"] = final_url + " (existing snapshot; LIVE FETCH FAILED, this is the archived copy)"
        if truncated:
            meta["truncated"] = f"first {MAX_BYTES} bytes only"
        ctype = headers.get_content_type()
        wiki = mediawiki_json(body) if ctype.endswith("json") else None
        if wiki:  # MediaWiki API answer: the page itself, not the JSON around it
            text, is_html, wtitle = wiki
            if is_html:
                p = TextExtractor()
                p.feed(text)
                p.close()
                text = p.text()
            meta["title"] = a.title or wtitle
            raw = (body, "raw.json")
        elif ctype in ("text/html", "application/xhtml+xml"):
            decoded, meta["charset"] = decode(body, headers.get_content_charset())
            p = TextExtractor()
            p.feed(decoded)
            p.close()
            text, meta["lang"] = p.text(), p.lang
            meta["title"] = a.title or " ".join(p.title.split())
            raw = (body, "raw.html")
        elif ctype == "application/pdf" or body[:5] == b"%PDF-":
            try:
                text, meta["pdf_text"] = pdf_text(body)
            except Exception as e:
                print(f"FAILED to extract text from the PDF at {a.url}: {e}", file=sys.stderr)
                sys.exit(1)
            if text is None:
                print(f"{a.url} is a PDF and no PDF text tool is installed; nothing saved. Ask the user to "
                      f"install one (`brew install poppler` or `pip install pypdf`) and run again, or use the "
                      f"fallback (--text-file, capture model-fetch).", file=sys.stderr)
                sys.exit(5)
            raw = (body, "original.pdf")
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

    if "archive" not in meta:
        meta["archive"] = "skipped" if a.no_archive else archive(page_url, a.archive)
    with Lock(a.research_dir):
        existing = stop_if_known(a.url)  # another agent may have saved it while this one downloaded
        save(a, meta, text, raw, index, existing)


def save(a, meta, text, raw, index, existing):
    sid = next_id_dir(os.path.join(a.research_dir, "sources"))
    folder = os.path.join(a.research_dir, "sources", sid)
    if raw:
        with open(os.path.join(folder, raw[1]), "wb") as f:
            f.write(raw[0])
    meta["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()  # check_quotes.py detects later edits
    front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in {"id": sid, **meta}.items() if v)
    with open(os.path.join(folder, "original.md"), "w", encoding="utf-8") as f:
        f.write(f"---\n{front}\n---\n\n{text}")

    entry = (f"## {sid} — {meta['title'] or meta['url']}\n- URL: {meta['url']}\n- Archive: {meta['archive']}\n"
             f"- Accessed: {meta['accessed'][:10]}\n- Language: {meta['lang']}\n- Capture: {meta['capture']}\n"
             f"- Author: \n- Published: \n- Type: \n- Rating: \n- Origin: \n- Subquestions: \n- Key phrases: \n- Notes: \n\n")
    with open(index, "a", encoding="utf-8") as f:
        f.write(("# Sources\n\n" if not existing else "") + entry)
    print(f"{sid} saved: {folder}/original.md ({len(text)} chars, lang={meta['lang'] or '?'}, "
          f"archive={meta['archive']})")


if __name__ == "__main__":
    main()
