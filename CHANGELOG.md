# Changelog

Research folders written by an older version keep working, but some need a small upgrade to
pass the newer checks. Each **Migration** note says what to change. The easiest way is to ask
the agent: "upgrade research/<slug> to the current format".

## 0.11.0

- `report.py` warns when `final.md` differs from what `build_final.py` builds (hand edits or
  a stale build). `final.md` ends with a "generated, don't edit" marker.
- Citations in `final.md` are linked titles plus an archive link instead of full URLs. A
  quote directly followed by `[C…]` gets one citation.
- `fetch.py` stores a sha256 of each saved text; `check_quotes.py` reports originals edited
  after saving.
- With `Rumors: leads-only` or `exclude`, citing a claim with credibility 3-6 in the draft is
  an error.
- `report.py` also warns about: a missing Settings block, Published fields that don't start
  with a date, ratings never mentioned in `factcheck-log.md`.
- [docs/enforcement.md](docs/enforcement.md): every rule and what enforces it.

**Migration:** rebuild `final.md` with `build_final.py` (a hand-written one now triggers a
warning). Sources saved earlier have no sha256 and are simply not checked.

## 0.10.0

- Claims no longer have an **As of** field: `report.py` computes it from the newest dated
  supporting evidence, and warns when newer evidence contradicts a claim.
- **Origin** in `sources.md` must be one short label (`rockstar`, `xhs-leak-2026-05`) or
  `own`; descriptions trigger a warning.
- New evidence review step: each evidence quote must state its claim. Headings count in the
  fact review.
- Published must start with `YYYY-MM-DD`.

**Migration:** delete `- As of:` lines from `claims.md` (or keep them; the report warns only
when they are newer than the evidence). Replace descriptive Origin values with labels,
giving the same origin the same label. Put the date first in Published.

## 0.9.0

- `Common knowledge` setting (default `off`): when `on`, background facts may be marked
  `[CK]` in the draft instead of becoming claims.

## 0.8.0

- Quote checks ignore encoding differences (Unicode normalization, full/half-width forms,
  invisible characters, curly quotes, dash variants).
- Duplicate URLs are detected after normalization (scheme, www/m./old./amp., tracking
  parameters, slash, fragment, encoding, redirects).
- PDF text extraction with `[page N]` markers via pdftotext or pypdf; exit code 5 when
  neither is installed.

## 0.7.0

- Methodologies (`open`, `journalism`, `academic`, or your own in `research/methodologies/`).
- A **Settings** block in `STATE.md`, quick and full setup modes, `research/PROFILE.md` for
  standing preferences.
- Citation styles in `build_final.py`: footnotes, numbered, author-date.
- Quote cuts marked `[...]` are accepted.

**Migration:** add the Settings block from `templates/STATE.md` to older `STATE.md` files,
moving User language, Reads and Limits into it.

## 0.6.0

- **Origin** field in `sources.md` and `report.py` (independent origins per claim, draft
  coverage, warnings, `summary.json`).

**Migration:** add `- Origin:` to each source entry.

## 0.5.0

- `build_final.py` generates `final.md` from `draft.md`.

## 0.4.0

- Bilingual translations (`sources/Sxxx/translation.<lang>.md`), verified against the
  original. **Reads** setting.

## 0.3.0

- Draft step with claim IDs `[C001]` and verified quotes; `final.md`. `check_quotes.py` also
  checks that every S/C ID exists.

## 0.2.0

- Admiralty ratings: source reliability A–F in `sources.md`, claim credibility 1–6 in
  `claims.md`, `factcheck-log.md`. `check_quotes.py`.
- Wayback fallback when a live page fails (`capture: wayback`).

**Migration:** key phrases go in backticks (`` `phrase` ``) instead of double quotes.
Source ratings are a letter plus a reason (`C — …`), without a number.

## 0.1.0

- Subquestion plan, verbatim source collection with `fetch.py`, `sources.md` index,
  `STATE.md`.
