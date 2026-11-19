# research-kit

An agent skill for evidence-first research for articles and essays. It works in Claude Code,
Codex and Gemini CLI: the skill is plain Markdown plus stdlib-only Python scripts.

What it does (v0.2):

- breaks a topic into subquestions and agrees the plan with you before searching
- searches in the languages the information comes from (Japanese, Ukrainian, English...),
  independent of the language you write in
- saves every source verbatim (`original.md` + `raw.html`) with URL, access date and Wayback
  snapshot, and indexes it in `sources.md` with exact key phrases for finding the fragment again
- writes the facts the text needs into `claims.md`, each with exact quotes as evidence
- rates sources (reliability A–F) and claims (credibility 1–6) with the Admiralty code, traces
  rumors back to their origin, and logs the reasoning in `factcheck-log.md`
- checks every quote by exact match against the saved original
- keeps the session state in `STATE.md`, so a new session picks up where the last one stopped

## Install

Replace `<owner>/<repo>` with wherever this repo is hosted.

**Claude Code** (plugin):

```sh
claude plugin marketplace add <owner>/<repo>
claude plugin install research-kit@research-kit
```

**Gemini CLI**:

```sh
gemini skills install https://github.com/<owner>/<repo>.git --path skills/research
```

**Codex** (also works for Gemini): both read `~/.agents/skills/`.

```sh
git clone https://github.com/<owner>/<repo>.git ~/src/research-kit
mkdir -p ~/.agents/skills && ln -s ~/src/research-kit/skills/research ~/.agents/skills/research
```

To develop locally in Claude Code, run `claude --plugin-dir .` in this repo.

Requires `python3` (3.9+).

## Use

Ask in any language, for example: *"Research how the localization of Mother 3 fan translation
was made, I'm writing an essay, write to me in Ukrainian"*. The agent creates
`./research/<slug>/`, proposes a plan, waits for your OK, then collects sources.
Next session: *"continue the mother-3 research"*.

## Research folder format

Any future tool or integration (Zotero, court archives, PDF import) only needs to produce this
layout. The easiest way is to register text through the same script:
`fetch.py <dir> <url> --text-file <file> --capture <tool-name>`.

```
research/<slug>/
  STATE.md              current state, read first
  plan.md               subquestions Q1..Qn: languages, queries, status
  sources.md            "## S001 — title" entries: URL, Archive, Accessed, Language,
                        Capture, Author, Published, Type, Rating, Subquestions,
                        Key phrases, Notes
  claims.md             "## C001 — claim" entries: Q, Credibility, Origin, Supports,
                        Contradicts, As of
  factcheck-log.md      append-only reasoning behind every rating
  sources/S001/
    original.md         YAML front matter + verbatim text. Never edited.
    raw.html            the page as downloaded (or original.pdf etc.)
```

`capture` records how the text was obtained: `script` (verbatim download), `user-paste`, or
`model-fetch` (possibly summarized by the agent's tool, so don't quote from it).

Quotes are written as S012 `exact text`; under a `## S012` heading a bare `text` belongs to
S012. `check_quotes.py <dir>` verifies them all.

## Roadmap

1. ✅ Plan, source collection, index, session state
2. ✅ Trust ratings (Admiralty code: source reliability A–F, information credibility 1–6),
   `claims.md`, fact-check log
3. Draft with quotes checked by exact match against originals
4. Translations stored next to originals (for reading only; the agent works from originals)

Known gaps: `fetch.py` can't read JavaScript-rendered pages and is blocked by some sites
(Cloudflare, 403); the skill falls back to the agent's own fetch tool or a user paste.

## Test

```sh
python3 skills/research/scripts/test_fetch.py
python3 skills/research/scripts/test_check_quotes.py
```
