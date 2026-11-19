"""Parsers for a research folder's sources.md and claims.md, shared by the scripts."""
import re

# S004 `quote` (origin: teaser-2026-06): the quote and the origin override are optional.
EVIDENCE = re.compile(r"\b(S\d{3,})\b(?::?\s*`[^`\n]*`)?(?:\s*\(origin:\s*([\w.:-]+)\))?")


def _field(block, name):
    m = re.search(r"^- " + re.escape(name) + r":[ \t]*(.*)$", block, re.M)
    return m.group(1).strip() if m else ""


def _list_field(block, name):
    """A field's text plus its indented continuation lines."""
    m = re.search(r"^- " + re.escape(name) + r":(.*(?:\n[ \t]+.*)*)", block, re.M)
    return m.group(1) if m else ""


def _blocks(text, prefix):
    for block in re.split(r"^(?=## " + prefix + r"\d{3,})", text, flags=re.M):
        m = re.match(r"## (" + prefix + r"\d{3,})[ \t]*(?:—[ \t]*(.*))?", block)
        if m:
            yield m.group(1), (m.group(2) or "").strip(), block


def _evidence(text):
    """[(source id, origin override or '')], in order, without repeats."""
    return list(dict.fromkeys(EVIDENCE.findall(text)))


def parse_sources(text):
    out = {}
    for sid, title, b in _blocks(text, "S"):
        url = _field(b, "URL").split()
        archive = re.search(r"https?://\S+", _field(b, "Archive"))
        rating = _field(b, "Rating")
        out[sid] = {
            "title": title,
            "url": url[0] if url else "",
            "archive": archive.group(0) if archive else "",
            "rating": rating[0] if rating[:1] in tuple("ABCDEF") else "",
            "origin": _field(b, "Origin"),
            "published": _field(b, "Published"),
            "type": _field(b, "Type"),
            "capture": _field(b, "Capture"),
        }
    return out


def parse_claims(text):
    out = {}
    for cid, title, b in _blocks(text, "C"):
        cred = re.match(r"\s*([1-6])", _field(b, "Credibility"))
        out[cid] = {
            "title": title,
            "credibility": cred.group(1) if cred else "",
            "as_of": _field(b, "As of"),
            "supports": _evidence(_list_field(b, "Supports")),
            "contradicts": _evidence(_list_field(b, "Contradicts")),
        }
    return out
