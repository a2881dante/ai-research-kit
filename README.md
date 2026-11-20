# research-kit

[![tests](https://github.com/a2881dante/ai-research-kit/actions/workflows/tests.yml/badge.svg)](https://github.com/a2881dante/ai-research-kit/actions/workflows/tests.yml)

An agent skill for evidence-first research for articles and essays. It works in Claude Code,
Codex and Gemini CLI: the skill is plain Markdown plus stdlib-only Python scripts.

## Why use it

Ask a model to research a topic and it writes a good article. What you can't easily do
afterwards is check it: which page a quote came from, whether the model actually read that
page, what a Japanese source really says, and how much each claim deserves to be trusted.

research-kit keeps all of that in one folder on disk:

- **Sources are saved, not just linked.** Every page is stored verbatim with its URL, access
  date and an archive link, so a quote can always be checked against what was read, even
  after the page changes or disappears.
- **Every quote is verified.** A script matches each quote against the saved original. A quote
  from a page that wasn't read, or with a changed word, fails the check.
- **Sources in any language, with translations next to them.** It searches in the languages
  the information comes from and gives you bilingual reading copies (original paragraph, then
  translation) of sources you can't read. The work itself is done from the originals.
- **Credibility in one place.** Each source gets a reliability rating and each claim a
  credibility rating, with the reasoning logged. Ten sites retelling one forum post count as
  one origin. Rumors stay in the research, labeled, and you decide how to use them.
- **It survives sessions.** The state, decisions and your preferences live in the folder, so
  a new session picks up where the last one stopped.

What it doesn't do: it doesn't make a strong model more accurate when the sources are already
in front of it. The measurements below show that. Its value is that the result can be checked,
and that the research is kept, not lost in a chat.

## Measured

Comparisons with the same model without the plugin, using Claude Code's `claude plugin eval`
(Opus 5.5 and Haiku 5.5, 3 runs per arm). Details, method and how to rerun:
[evals/README.md](evals/README.md).

| | With research-kit | Without |
|---|---|---|
| Accuracy of the final article on a given set of sources with planted traps (price error, single-origin rumor retold 10 times, fake leak, Japanese-only release delay, similarly named games, resumed session): 48 runs | same | same |
| Live research from scratch (the Shenmue budget): quotes from sources found on the cited page | Opus 16 of 16, Haiku 5 of 5 | Opus 36 of 40 (4 cite live pages closed to bots that were read through an archive), Haiku 29 of 32 (one changed word, one quote from a page the model couldn't open) |
| Contested topic, sources in English and Japanese, article in Ukrainian (Silent Hills): translated quotes that come with their checked original | Opus 16 of 22, Haiku 8 of 8 | 0 of 56 |
| Vague request: checks with you (languages, audience, rumors, depth) before researching | 6 of 6 | 0 of 6 (researches on its own assumptions; Opus spends $1–2 on it) |
| Saved originals, translations, rated claims, fact-check log, archive links | yes (protocol followed in 40 of 42 plugin runs) | no |
| Cost per article, Opus 5.5 | $1–5 | $0.4–2 |
| Time per article | about 2–3x | 1x |

## Features (v0.12)

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

**Claude Code** (plugin):

```sh
claude plugin marketplace add a2881dante/ai-research-kit
claude plugin install research-kit@research-kit
```

**Gemini CLI**:

```sh
gemini skills install https://github.com/a2881dante/ai-research-kit.git --path skills/research
```

**Codex** (also works for Gemini): both read `~/.agents/skills/`.

```sh
git clone https://github.com/a2881dante/ai-research-kit.git ~/src/research-kit
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

Done: plan and collection, ratings and fact-check log, drafts with verified quotes,
translations, methodologies, origins report, generated final copy, eval suite.

Next:

- `fetch.py` can't read JavaScript-rendered pages and is blocked by some sites (Cloudflare,
  403). The skill falls back to the agent's own fetch tool or a user paste; a better path is
  the most useful improvement left.
- More live eval topics (a contested topic with paywalled sources, a non-English one).
- Check the install on Codex and Gemini CLI (so far only Claude Code is tested).

## Test

CI runs these with Python 3.13 on Linux and macOS, and with 3.9 on macOS (`.github/workflows/tests.yml`).

```sh
python3 skills/research/scripts/tests/test_fetch.py
python3 skills/research/scripts/tests/test_check_quotes.py
python3 skills/research/scripts/tests/test_build_final.py
python3 skills/research/scripts/tests/test_report.py
```

## License

MIT, see [LICENSE](LICENSE).
