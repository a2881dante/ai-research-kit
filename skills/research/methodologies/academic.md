---
name: academic
description: Scholarly papers and theses. Peer-reviewed and primary sources, no rumors, wikis only as leads, author-date citations.
---

# Academic

Conventions differ by field (humanities, social sciences, STEM) and by journal. If the user
names a journal or style guide (APA, Chicago, MLA, ГОСТ), follow it where it differs from
this file.

## Settings

- Rumors: exclude
- Citation style: author-date
- Translations: offer
- Depth: deep

## Sources

- In the text: peer-reviewed papers, books from academic publishers, primary documents
  (official records, datasets, court records, original interviews, the work being studied).
- Press: secondary context only, attributed.
- Wikipedia, wikis, blogs: leads only, never cited. Find and cite what they cite.
- Forums, imageboards, social media: only when they are the object of study (an essay about
  a fan community, a study of how a rumor spread). Then they are primary data: cite with
  date, author or handle, and archive link.
- Record a DOI when there is one (in Notes, and as the URL `https://doi.org/...` if it
  resolves).

## Confirmation

- Credibility 1 needs a saved primary source or a peer-reviewed source.
- Claims supported only by press stay at 2 or lower and are attributed in the text.

## In the text

- Hedge according to credibility ("suggests", "according to", "it has been claimed").
- Keep your own argument visibly separate from what sources say.
- Paraphrases are cited as well as quotes.
- When a source has pages (books, PDFs: see the `[page N]` markers in `original.md`), note the
  page in the claim's evidence line, such as
  `` - S004 `exact quote` (p. 37) ``, and give it in the text.

## Extra checks

- Every paragraph with factual content has at least one citation.
- No tertiary sources (wikis, encyclopedias) among the cited sources.
- `final.md` is a generated author-date list: check it against the required style guide by
  hand before submitting.
