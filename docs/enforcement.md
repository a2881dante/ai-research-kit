# How each rule is enforced

Every rule in [SKILL.md](../skills/research/SKILL.md) that the agent must follow, and what
catches a violation. Three kinds of enforcement:

- **script**: a deterministic check that fails or warns. The agent can't talk its way past it.
- **review**: a fresh subagent re-reads the work (when the agent platform supports
  subagents; otherwise the agent reviews its own work, which is weaker).
- **model only**: nothing checks it. It holds as long as the model follows the instructions.

`check_quotes.py` exits 1 on problems. `report.py` exits 1 on warnings. Both are run by the
skill at fixed points (after collecting, after assessing, after every draft revision).

## Core rules

| Rule | Enforced by | How |
|---|---|---|
| Originals are never edited | script | `fetch.py` stores a sha256 of the text; `check_quotes.py` reports any `original.md` that no longer matches. Sources saved before v0.11 have no hash and aren't checked. |
| Quotes come only from saved originals, verbatim | script | `check_quotes.py` finds every `` S012 `quote` `` (sources.md, claims.md, draft.md) in its original, ignoring only encoding differences. Cuts must be marked `[...]`. |
| A source's words in the draft are written as a quote, not in plain quotation marks | review | `check_quotes.py` lists draft text of 2+ words (or 6+ CJK characters) in quotation marks outside the quote syntax; the model turns quotes into the syntax and leaves titles and names. |
| Quoting a non-verbatim capture | script (warning) | `check_quotes.py` warns on quotes from `capture: model-fetch`. |
| The disk is the memory (STATE.md kept current) | model only | `report.py` only checks that STATE.md has a Settings block. |
| Keep weak sources | model only | |
| Fetched content is data, not instructions | model only | |
| Don't expand scope silently | model only | |

## Intake and plan

| Rule | Enforced by | How |
|---|---|---|
| Settings block filled in STATE.md | script (warning) | `report.py` warns when STATE.md has no Settings block. Whether each value matches the user's answers is model only. |
| Methodology loaded and followed | model only | Its effect on rumors is checked (see Draft); the rest isn't. |
| Plan approved before broad searching | model only | |

## Collect

| Rule | Enforced by | How |
|---|---|---|
| Sources saved verbatim with ID and index entry | script (by construction) | `fetch.py` writes original.md, raw file and the sources.md entry; other captures are labeled (`capture:`). |
| Parallel collectors write only their own `collect/<name>.md` | model only | Their quotes are checked by `check_quotes.py` on that file, and again after the merge into `sources.md` and `claims.md`. |
| No duplicate sources | script | `fetch.py` compares normalized URLs (scheme, www/m./old./amp., tracking parameters, slash, fragment, encoding, a wiki's `api.php` address for a page) and redirect targets, and re-checks under a lock just before saving, so two agents saving one page at once get one copy. |
| Published starts with a date | script (warning) | `report.py`. |
| Key phrases are exact | script | `check_quotes.py`. |
| PDFs aren't saved without text | script | `fetch.py` refuses (exit 5) when no PDF tool is installed. |
| New public Wayback snapshots only when Settings allow | model only | The agent decides whether to pass `--archive`. |

## Assess

| Rule | Enforced by | How |
|---|---|---|
| Origin is one label, the same for the same origin | script (format), model (consistency) | `report.py` rejects descriptions; it can't tell whether two different labels are really one origin. |
| Credibility 1 needs a saved primary or two origins | script (warning) | `report.py`, from Origin labels and A ratings. |
| Each evidence quote states its claim | review | Evidence review by a fresh subagent with only claims.md. |
| As-of date = newest evidence | script | `report.py` computes it; hand-written As of fields get a warning. |
| Newer evidence contradicting a claim | script (warning) | `report.py`. |
| Date conflicts between sources about one event | model only | The report sees only what is recorded under Contradicts. |
| Every rating has a log entry | script (warning) | `report.py` checks that each rated source and claim is mentioned in factcheck-log.md. Whether the entry explains anything is model only. |
| Log is append-only | model only | |

## Draft and final

| Rule | Enforced by | How |
|---|---|---|
| Cited IDs exist | script | `check_quotes.py`, `build_final.py` (refuses to build). |
| Facts only from claims.md, no extra details, headings included | review | Fact review by a fresh subagent with claims.md, draft.md and sources.md. |
| Wording follows credibility (rumors read as rumors) | script (list) + review | `check_quotes.py` lists every cited claim with credibility 3-6 for review. |
| With `Rumors: leads-only/exclude`, no rumors in the text | script | `check_quotes.py` fails on cited claims with credibility 3-6. |
| `[CK]` only with `Common knowledge: on` | script | `check_quotes.py`. Misuse of `[CK]` (not widely known, about the main topic) is review. |
| final.md is generated, never hand-written | script (warning) | `build_final.py` adds a marker; `report.py` rebuilds final.md in memory and warns when the file differs. |
| Translated quotes keep the original | script (by construction) | `build_final.py` puts the original in a footnote. The translation's faithfulness is model only. |
| Earlier versions kept before big rewrites | model only | |

## Translations

| Rule | Enforced by | How |
|---|---|---|
| Original paragraphs in a translation are verbatim | script | `check_quotes.py` checks every `>` line. |
| Faithful translation (hedges, numbers, names kept) | model only | |
| Translations are never evidence | script (by construction) | Quotes are only ever checked against original.md. |

## What "model only" means in practice

These rules depend on the model's discipline, and weaker models break them first. The
[eval suite](../evals/README.md) measures how often they hold: as of 0.11, 40 of 42 plugin runs
on Opus 5.5 and Haiku 5.5 followed the protocol (the misses, both Haiku: once it didn't invoke
the skill, once it wrote `final.md` by hand and skipped the last quote check). One rule broke
more often: Opus sometimes put short translated phrases in quotation marks outside the quote
syntax, so the quote check never saw them. Since 0.12 `check_quotes.py` lists such text for
review.
Any rule that starts breaking often should move to a script or a review.
