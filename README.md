# research-kit

An agent skill for evidence-first research for articles and essays. It works in Claude Code,
Codex and Gemini CLI: the skill is plain Markdown plus stdlib-only Python scripts.

What it does (v0.11):

- works by a methodology you pick: `open` (default: everything, rumors labeled), `journalism`
  (attribution, two-source rule, rumors only as news), `academic` (peer-reviewed and primary
  sources, no rumors, author-date citations), or your own
- quick setup by default, or a full questionnaire ("full setup"); standing preferences live in
  `research/PROFILE.md` so they aren't asked again
- every fact in the text goes through collection and fact-checking; for overview texts you can
  switch on `Common knowledge`, which lets background facts be marked `[CK]` instead (listed for
  review, never about the main topic)
- breaks a topic into subquestions and agrees the plan with you before searching
- searches in the languages the information comes from (Japanese, Ukrainian, English...),
  independent of the language you write in
- saves every source verbatim (`original.md` + `raw.html`) with URL, access date and Wayback
  snapshot, and indexes it in `sources.md` with exact key phrases for finding the fragment again
- writes the facts the text needs into `claims.md`, each with exact quotes as evidence
- rates sources (reliability A–F) and claims (credibility 1–6) with the Admiralty code, traces
  rumors back to their origin, and logs the reasoning in `factcheck-log.md`
- drafts the text from the assessed claims: every fact cites its claim, rumors are worded as
  rumors, quotes keep the original next to the translation; earlier versions are kept
- generates the clean copy (`final.md`) from the draft with a script: claim IDs become
  footnotes with sources and archive links, so the two can't drift apart
- translates sources you can't read into your language as a bilingual reading copy
  (original paragraph, then translation); the agent itself keeps working from originals
- checks every quote by exact match against the saved original, and every claim/source ID
- `report.py` counts independent origins per claim (ten reposts of one leak = one origin),
  shows draft coverage and warns about weak spots; `summary.json` is machine-readable
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

Requires `python3` (3.9+). For text from PDFs, install `pdftotext` (`brew install poppler`)
or `pypdf` (`pip install pypdf`); without them PDFs are refused with a hint.

Permissions in Claude Code: the skill pre-approves its own scripts, but only for the turn in
which it was invoked. If Claude asks again later, choose "always allow" for that script.

## Use

Ask in any language, for example: *"Research how the localization of Mother 3 fan translation
was made, I'm writing an essay, write to me in Ukrainian"*. The agent creates
`./research/<slug>/`, proposes a plan, waits for your OK, then collects sources.
Next session: *"continue the mother-3 research"*.

## Methodologies

Built in: [open](skills/research/methodologies/open.md),
[journalism](skills/research/methodologies/journalism.md),
[academic](skills/research/methodologies/academic.md). To add your own (an outlet's style
guide, Wikipedia's rules, a journal's requirements), copy one of them into
`research/methodologies/<name>.md` next to your research folders and edit it; files there win
over built-in ones with the same name and survive plugin updates. Keep the same sections
(Settings, Sources, Confirmation, In the text, Extra checks). A methodology can only make the
work stricter: verbatim originals, quote checks and the fact-check log always apply.

## Research folder format

Any future tool or integration (Zotero, court archives, PDF import) only needs to produce this
layout. The easiest way is to register text through the same script:
`fetch.py <dir> <url> --text-file <file> --capture <tool-name>`.

```
research/
  PROFILE.md            your standing preferences (languages, default methodology...)
  methodologies/        your own methodologies
research/<slug>/
  STATE.md              current state and Settings, read first
  plan.md               subquestions Q1..Qn: languages, queries, status
  sources.md            "## S001 — title" entries: URL, Archive, Accessed, Language,
                        Capture, Author, Published, Type, Rating, Origin, Subquestions,
                        Key phrases, Notes
  claims.md             "## C001 — claim" entries: Q, Credibility, Origin, Supports,
                        Contradicts (as-of dates are computed by report.py)
  factcheck-log.md      append-only reasoning behind every rating
  draft.md              the text; facts cite [C001], quotes S012 `original` — «translation»
  draft.v1.md ...       earlier versions
  final.md              clean copy for publishing, generated by build_final.py
  summary.json          generated by report.py
  sources/S001/
    original.md         YAML front matter + verbatim text. Never edited.
    raw.html            the page as downloaded (or original.pdf etc.)
    translation.ru.md   bilingual reading copy: "> original paragraph" + translation
```

`capture` records how the text was obtained: `script` (verbatim download), `user-paste`, or
`model-fetch` (possibly summarized by the agent's tool, so don't quote from it), or `wayback`
(the live page failed and `fetch.py` saved the closest Wayback snapshot instead).

Quotes are written as S012 `exact text`; under a `## S012` heading a bare `text` belongs to
S012. `check_quotes.py <dir>` verifies them all.

## Upgrading

[CHANGELOG.md](CHANGELOG.md) lists what changed in each version and how to upgrade research
folders made by an older one. The report and the quote check also say what to fix.

## How rules are enforced

[docs/enforcement.md](docs/enforcement.md) lists every rule the agent must follow and what
catches a violation: a script, a fresh-subagent review, or nothing ("model only").

## Roadmap

1. ✅ Plan, source collection, index, session state
2. ✅ Trust ratings (Admiralty code: source reliability A–F, information credibility 1–6),
   `claims.md`, fact-check log
3. ✅ Draft with quotes checked by exact match against originals
4. ✅ Translations stored next to originals (for reading only; the agent works from originals)

Known gaps: `fetch.py` can't read JavaScript-rendered pages and is blocked by some sites
(Cloudflare, 403); the skill falls back to the agent's own fetch tool or a user paste.

## Test

CI runs these on Linux and macOS with Python 3.9 and 3.13 (`.github/workflows/tests.yml`).

```sh
python3 skills/research/scripts/tests/test_fetch.py
python3 skills/research/scripts/tests/test_check_quotes.py
python3 skills/research/scripts/tests/test_build_final.py
python3 skills/research/scripts/tests/test_report.py
```

## License

MIT, see [LICENSE](LICENSE).
