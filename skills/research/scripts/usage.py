#!/usr/bin/env python3
"""Tokens spent on a research folder, and what they would cost at API list prices.

  python3 usage.py research/<slug> [--json]

Reads Claude Code session logs (~/.claude/projects, or $CLAUDE_CONFIG_DIR/projects), subagents
included. Which sessions belong to the research comes from the `Sessions:` line in STATE.md
(the skill records each session there). Without it, sessions that mention research/<slug> are
in which a skill script ran on research/<slug>. Sessions are counted whole either way.

The cost is an estimate at API list prices: on a Pro/Max subscription you don't pay it. Other
agents (Codex, Gemini CLI) keep logs in other formats and aren't counted. Web searches are
counted per call at the API search price; the tokens of Claude Code's search requests aren't
in its logs.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

PRICES_AS_OF = "2026-11-03"
# $ per million tokens: input, output, cache read. Cache writes cost 1.25x input (5 min) or
# 2x input (1 hour); fast mode costs 2x. Matched by prefix of the model id.
PRICES = {
    "claude-fable-5-2": (8, 40, 0.20), "claude-mythos-5-2": (8, 40, 0.20),
    "claude-fable-5-1": (10, 50, 0.25), "claude-mythos-5-1": (10, 50, 0.25),
    "claude-fable-5": (10, 50, 1.00), "claude-mythos-5": (10, 50, 1.00),
    "claude-opus-5-5": (4, 20, 0.20), "claude-opus-5": (5, 25, 0.50),
    "claude-opus-4-8": (5, 25, 0.50), "claude-opus-4-7": (5, 25, 0.50),
    "claude-opus-4-6": (5, 25, 0.50), "claude-opus-4-5": (5, 25, 0.50),
    "claude-sonnet-5-5": (2, 10, 0.10), "claude-sonnet-5": (2, 10, 0.20),
    "claude-sonnet-4-6": (3, 15, 0.30), "claude-sonnet-4-5": (3, 15, 0.30),
    "claude-haiku-5-5": (0.10, 0.50, 0.01), "claude-haiku-4-5": (1, 5, 0.10),
}
HAIKU_55_LONG = (0.50, 2.50, 0.05)  # Haiku 5.5 prompts over 100K tokens
WEB_SEARCH = 0.01  # $ per search
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
FIELDS = ("input", "cache_write", "cache_read", "output", "web_searches")


def price(model, prompt_tokens):
    key = max((k for k in PRICES if model.startswith(k)), key=len, default=None)
    if key == "claude-haiku-5-5" and prompt_tokens > 100_000:
        return HAIKU_55_LONG
    return PRICES.get(key)


def cost(model, u):
    """$ for one API response, or None for a model without a known price."""
    prompt = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
    p = price(model, prompt)
    if not p:
        return None
    inp, out, read = p
    cc = u.get("cache_creation") or {}
    w1h = cc.get("ephemeral_1h_input_tokens", 0)
    w5m = u.get("cache_creation_input_tokens", 0) - w1h
    usd = (u.get("input_tokens", 0) * inp + w5m * inp * 1.25 + w1h * inp * 2
           + u.get("cache_read_input_tokens", 0) * read + u.get("output_tokens", 0) * out) / 1e6
    if u.get("speed") == "fast":
        usd *= 2
    return usd + (u.get("server_tool_use") or {}).get("web_search_requests", 0) * WEB_SEARCH


def session_files(projects, sid):
    """The session's main log and its subagents' logs."""
    return (glob.glob(os.path.join(projects, "*", sid + ".jsonl"))
            + glob.glob(os.path.join(projects, "*", sid, "subagents", "*.jsonl")))


def recorded_sessions(research_dir):
    try:
        with open(os.path.join(research_dir, "STATE.md"), encoding="utf-8") as f:
            line = next((ln for ln in f if ln.lstrip("- ").startswith("Sessions:")), "")
    except FileNotFoundError:
        return []
    return list(dict.fromkeys(UUID.findall(line)))


def guessed_sessions(projects, slug):
    """Sessions in which the agent or a subagent ran a skill script on research/<slug>."""
    folder = re.compile(r"research/" + re.escape(slug) + r"(?![\w-])")  # not research/<slug>-v2
    script = re.compile(r"(fetch|check_quotes|report|build_final)\.py")
    found = []
    for path in glob.glob(os.path.join(projects, "*", "*.jsonl")):
        sid = os.path.basename(path)[:-6]
        for p in session_files(projects, sid):
            with open(p, encoding="utf-8", errors="replace") as f:
                if any('"tool_use"' in ln and script.search(ln) and folder.search(ln) for ln in f):
                    found.append(sid)
                    break
    return found


def tally(paths):
    """Per-model token sums for a set of logs; each API response counted once."""
    seen, models, first, last = set(), defaultdict(lambda: defaultdict(float)), None, None
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"usage"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                m = d.get("message") or {}
                u, model = m.get("usage"), m.get("model") or ""
                if d.get("type") != "assistant" or not u or model.startswith("<"):
                    continue
                t = models[model]
                # Claude Code's WebSearch runs as a separate request that isn't in the log: count the calls
                searches = sum(1 for b in m.get("content") or [] if isinstance(b, dict)
                               and b.get("type") == "tool_use" and b.get("name") == "WebSearch")
                t["web_searches"] += searches
                t["cost"] += searches * WEB_SEARCH
                key = m.get("id") or d.get("requestId") or d.get("uuid")  # a response is logged once per content block
                if key in seen:
                    continue
                seen.add(key)
                t["input"] += u.get("input_tokens", 0)
                t["cache_write"] += u.get("cache_creation_input_tokens", 0)
                t["cache_read"] += u.get("cache_read_input_tokens", 0)
                t["output"] += u.get("output_tokens", 0)
                t["web_searches"] += (u.get("server_tool_use") or {}).get("web_search_requests", 0)
                c = cost(model, u)
                t["cost"] += c or 0
                t["unpriced"] += c is None
                ts = d.get("timestamp", "")[:10]
                first, last = min(first or ts, ts), max(last or ts, ts)
    return models, first, last


def human(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else str(int(n))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("research_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    projects = os.path.join(base, "projects")
    slug = os.path.basename(os.path.normpath(a.research_dir))
    sids = recorded_sessions(a.research_dir)
    guessed = not sids
    if guessed:
        sids = guessed_sessions(projects, slug)
    rows, total = [], defaultdict(lambda: defaultdict(float))
    for sid in sids:
        paths = session_files(projects, sid)
        if not paths:
            rows.append({"session": sid, "missing": True})
            continue
        models, first, last = tally(paths)
        for model, t in models.items():
            for k, v in t.items():
                total[model][k] += v
        rows.append({"session": sid, "date": first, "last": last, "subagents": len(paths) - 1,
                     "tokens": sum(sum(t[k] for k in FIELDS[:4]) for t in models.values()),
                     "cost": sum(t["cost"] for t in models.values())})
    out = {"research": slug, "sessions_from": "guessed" if guessed else "STATE.md", "prices_as_of": PRICES_AS_OF,
           "models": {m: dict(t) for m, t in total.items()}, "sessions": rows,
           "cost_usd": round(sum(t["cost"] for t in total.values()), 2)}
    if a.json:
        json.dump(out, sys.stdout, indent=2)
        print()
        return
    if not sids:
        print(f"No Claude Code sessions found for research/{slug}.")
        return
    src = ("sessions that ran the skill scripts on research/" + slug + " (guessed: STATE.md has no Sessions line)"
           if guessed else "sessions listed in STATE.md")
    print(f"research/{slug}: {len(sids)} sessions, from {src}\n")
    print(f"{'model':<22}{'input':>9}{'cache wr':>10}{'cache rd':>10}{'output':>9}{'search':>8}{'cost':>10}")
    for model, t in sorted(total.items(), key=lambda kv: -kv[1]["cost"]):
        c = f"${t['cost']:.2f}" + ("*" if t["unpriced"] else "")
        print(f"{model:<22}{human(t['input']):>9}{human(t['cache_write']):>10}{human(t['cache_read']):>10}"
              f"{human(t['output']):>9}{int(t['web_searches']):>8}{c:>10}")
    print(f"{'total':<68}${out['cost_usd']:.2f}")
    if any(t["unpriced"] for t in total.values()):
        print("* no price known for this model; its tokens aren't in the cost")
    print("\nSessions:")
    for r in rows:
        if r.get("missing"):
            print(f"  {r['session']}  log not found")
        else:
            print(f"  {r['session'] if guessed else r['session'][:8]}  {r['date']}{'..' + r['last'] if r['last'] != r['date'] else ''}"
                  f"  {r['subagents']} subagents  {human(r['tokens'])} tokens  ${r['cost']:.2f}")
    if guessed:
        print("\nTo count only the right sessions, list their ids in STATE.md: - Sessions: <id>, <id>")
    print(f"\nCost at API list prices as of {PRICES_AS_OF}; on a Pro/Max subscription you don't pay it."
          " Sessions are counted whole.")


if __name__ == "__main__":
    main()
