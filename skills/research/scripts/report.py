#!/usr/bin/env python3
"""Summarize a research folder: claims, independent origins, draft coverage, warnings.

  report.py <research_dir> [--json PATH]

Writes summary.json (default: <research_dir>/summary.json; generated, never edit it) and
prints a readable summary. Independence counts distinct origins, not sources: a source's
Origin field in sources.md ("own" = the source itself is the origin), overridden per evidence
line in claims.md with "(origin: label)".
Exit 0 if there are no warnings, 1 otherwise.
"""
import argparse
import json
import os
import re
import sys

from research_files import parse_claims, parse_sources


def first_date(text):
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return m.group(0) if m else ""


def read(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def report(sources, claims, draft):
    warnings = []

    def origin(sid, override=""):
        o = override or sources.get(sid, {}).get("origin", "")
        return sid if o in ("", "own") else o  # a missing origin was already warned about

    for sid, s in sources.items():
        if not s["rating"]:
            warnings.append(f"{sid}: no Rating letter")
        if not s["origin"]:
            warnings.append(f"{sid}: no Origin")

    cited = {}
    # outline comments (<!-- claims: ... -->) don't count; keep line numbers intact
    draft = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), draft, flags=re.S)
    for ln, line in enumerate(draft.splitlines(), 1):
        for cid in set(re.findall(r"\b(C\d{3,})\b", line)):
            cited.setdefault(cid, []).append(ln)

    out_claims = {}
    for cid, c in claims.items():
        sup = [sid for sid, _ in c["supports"]]
        contra = [sid for sid, _ in c["contradicts"]]
        for sid in sup + contra:
            if sid not in sources:
                warnings.append(f"{cid}: unknown source {sid}")
        origins = list(dict.fromkeys(origin(sid, o) for sid, o in c["supports"]))
        primary = [sid for sid in sup if sources.get(sid, {}).get("rating") == "A"]
        if not c["credibility"]:
            warnings.append(f"{cid}: no Credibility")
        if not sup:
            warnings.append(f"{cid}: no Supports")
        elif c["credibility"] == "1" and not primary and len(origins) < 2:
            warnings.append(f"{cid}: credibility 1, but one origin ({origins[0]}) and no A-rated source")
        dates = [first_date(sources[s]["published"]) for s in sup + contra if s in sources]
        newest, as_of = max(filter(None, dates), default=""), first_date(c["as_of"])
        if as_of and newest and as_of > newest:
            warnings.append(f"{cid}: As of {as_of} is newer than any evidence ({newest})")
        out_claims[cid] = {"title": c["title"], "credibility": c["credibility"], "as_of": c["as_of"],
                           "supports": sup, "contradicts": contra, "origins": origins,
                           "independent_origins": len(origins), "draft_lines": cited.get(cid, [])}
    for cid in cited:
        if cid not in claims:
            warnings.append(f"draft: unknown claim {cid}")

    out_sources = {sid: {**s, "claims": [cid for cid, c in out_claims.items() if sid in c["supports"]]}
                   for sid, s in sources.items()}
    groups = {}
    for sid, s in sources.items():
        if s["origin"] and s["origin"] != "own":
            groups.setdefault(s["origin"], []).append(sid)
    unused = [cid for cid in claims if cid not in cited] if cited else []
    ck = [ln for ln, line in enumerate(draft.splitlines(), 1) if "[CK]" in line]
    return {"claims": out_claims, "sources": out_sources, "origins": groups,
            "unused_in_draft": unused, "common_knowledge_lines": ck, "warnings": warnings}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("research_dir")
    ap.add_argument("--json", help="where to write the summary (default: <research_dir>/summary.json)")
    a = ap.parse_args()
    rd = a.research_dir
    r = report(parse_sources(read(os.path.join(rd, "sources.md"))),
               parse_claims(read(os.path.join(rd, "claims.md"))),
               read(os.path.join(rd, "draft.md")))

    print("Claims: credibility, independent origins, draft lines")
    for cid, c in r["claims"].items():
        lines = ",".join(map(str, c["draft_lines"])) or "-"
        print(f"  {cid}  {c['credibility'] or '?'}  {c['independent_origins']} origin(s): "
              f"{', '.join(c['origins']) or '-'}  draft:{lines}")
    if r["origins"]:
        print("Shared origins (one origin behind several sources):")
        for o, sids in r["origins"].items():
            print(f"  {o}: {', '.join(sids)}")
    if r["common_knowledge_lines"]:
        print(f"Common-knowledge facts [CK], not checked: draft lines {', '.join(map(str, r['common_knowledge_lines']))}")
    if r["unused_in_draft"]:
        print(f"Not used in draft: {', '.join(r['unused_in_draft'])}")
    if r["warnings"]:
        print("Warnings:")
        for w in r["warnings"]:
            print(f"  {w}")
    path = a.json or os.path.join(rd, "summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(f"{len(r['claims'])} claims, {len(r['sources'])} sources, {len(r['warnings'])} warnings; wrote {path}")
    sys.exit(1 if r["warnings"] else 0)


if __name__ == "__main__":
    main()
