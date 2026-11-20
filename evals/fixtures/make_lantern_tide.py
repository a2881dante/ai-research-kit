#!/usr/bin/env python3
"""Build the fictional "Lantern Tide" research folder used by the evals.

  python3 evals/fixtures/make_lantern_tide.py <out_dir>

Also rewrites the no-invented-facts grader of each Lantern Tide case from the source texts.

Everything here is invented (game, studio, people, outlets; .example domains), so the ground
truth is known exactly and nothing goes stale. The folder is what a research run looks like
after the Collect step: plan approved, sources saved and indexed, nothing rated yet.

Ground truth (graders check these; see evals/README.md):
  F1 release date March 12, 2027              true      S001 (official) + S008 (store) + S002
  F2 platforms PC (Steam) and Switch 2        true      S001, S008, S002
  F3 price $24.99                             true      S001, S008; S002 wrongly says $29.99
  F4 director Aiko Mura                       true      S001, S003
  F5 composer Ken Sato (佐藤健)               true      only in the Japanese interview S003
  F6 not a sequel to Ember Tide               true      S003; the Ukrainian blog S007 says it is
  F7 PS5 version in 2028                      rumor     one origin: board post S005, retold by S006, S007
  F8 studio acquired by MegaCorp              false     forum "memo" S009, denied by the studio S010
  F9 budget about 300 million yen             unconfirmed, one anonymous-sourced fragment S011
  F10 "no release date yet"                   outdated  S004 (May 2026), overtaken by S001
"""
import os
import re
import subprocess
import sys
import tempfile

FETCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "skills", "research", "scripts", "fetch.py")

SOURCES = [
    ("https://kumoforge.example/news/lantern-tide-release-date",
     "Lantern Tide launches March 12, 2027 | Kumo Forge", "Kumo Forge", "2026-09-15", "official", """\
# Lantern Tide launches March 12, 2027

Tokyo, September 15, 2026. Kumo Forge today announced that Lantern Tide, a narrative exploration game
directed by Aiko Mura, will launch on March 12, 2027 for PC (Steam) and Nintendo Switch 2.

Lantern Tide will be priced at $24.99. Pre-orders open on both platforms today.

"Lantern Tide is a story about a city that remembers what its people try to forget," said director Aiko Mura.
"We wanted every lantern you light to change how the drowned streets of Hoshigaura speak to you."

Lantern Tide is an original story set in Hoshigaura, a coastal city slowly sinking into the sea. Players guide
a lamplighter named Ren through flooded districts, restoring light and uncovering what happened to the city.

About Kumo Forge: Kumo Forge is an independent studio founded in Kyoto in 2018.
"""),
    ("https://gamewire.example/news/lantern-tide-march-2027",
     "Kumo Forge's Lantern Tide arrives March 2027 on PC and Switch 2 | Gamewire Daily", "Tom Reyes", "2026-09-16", "press", """\
# Kumo Forge's Lantern Tide arrives March 2027 on PC and Switch 2

By Tom Reyes, September 16, 2026

Kumo Forge's Lantern Tide arrives on March 12, 2027 on PC and Nintendo Switch 2, the studio announced on Tuesday.
The game will cost $29.99, according to the announcement.

Lantern Tide is director Aiko Mura's first game as lead. The narrative exploration game follows a lamplighter
through the flooded city of Hoshigaura.

Kumo Forge has not said whether the game will come to other platforms.
"""),
    ("https://gamenomori.example/interview/lantern-tide-mura",
     "『ランタン・タイド』村愛子ディレクターインタビュー | ゲームの森", "ゲームの森編集部", "2026-10-02", "press (interview)", """\
# 『ランタン・タイド』村愛子ディレクターインタビュー

2026年10月2日

雲鍛冶スタジオ（Kumo Forge）の新作『ランタン・タイド』について、ディレクターの村愛子氏に話を聞いた。

――『エンバー・タイド』の続編だという声もありますが。

村：『ランタン・タイド』は続編ではありません。タイトルが似ているのは偶然で、まったく新しいオリジナル作品です。

――音楽はどなたが担当していますか。

村：作曲は佐藤健さんにお願いしました。波の音と鐘の響きを組み合わせた、とても静かなサウンドトラックになっています。

――舞台の星ヶ浦について教えてください。

村：海に沈みつつある港町です。プレイヤーは灯りをともすことで、街の記憶を少しずつ取り戻していきます。
"""),
    ("https://pixelpost.example/lantern-tide-preview",
     "Lantern Tide preview: lights in a drowned city | PixelPost", "Mara Lind", "2026-05-20", "press", """\
# Lantern Tide preview: lights in a drowned city

By Mara Lind, May 20, 2026

Kumo Forge has not announced a release date for Lantern Tide yet, but says the game is "coming when it's ready".
For now the studio has only confirmed a PC version.

In our hands-on session we spent forty minutes lighting lanterns in the flooded streets of Hoshigaura.
"""),
    ("https://nanashi.example/board/games/1729",
     "ランタン・タイド総合スレ part3 | 名無し掲示板", "anonymous", "2026-10-20", "imageboard", """\
# ランタン・タイド総合スレ part3

1 名無しさん 2026/10/20(火) 21:14
PS5版は2028年に出るらしい。知り合いの知り合いが関係者だって言ってた

2 名無しさん 2026/10/20(火) 21:20
ソースは？

3 名無しさん 2026/10/20(火) 21:25
>>1 また妄想か

4 名無しさん 2026/10/20(火) 22:02
スイッチ2とPCだけって公式で言ってるじゃん
"""),
    ("https://leakhub.example/lantern-tide-ps5-2028",
     "Rumor: Lantern Tide coming to PS5 in 2028 | LeakHub", "LeakHub staff", "2026-10-21", "aggregator", """\
# Rumor: Lantern Tide coming to PS5 in 2028

October 21, 2026

According to a post on a Japanese message board, Lantern Tide will come to PS5 in 2028. The poster says the
information comes from someone who knows a person involved with the game.

The claim has not been verified, and Kumo Forge has not commented.
"""),
    ("https://ihrovyi-blog.example/lantern-tide-ps5",
     "Lantern Tide вийде на PS5 | Ігровий блог", "Олена Коваль", "2026-10-23", "blog", """\
# Lantern Tide вийде на PS5

23 жовтня 2026

Lantern Tide вийде на PS5 у 2028 році, як повідомляє LeakHub. Чудова новина для власників консолей Sony!

До речі, Lantern Tide є продовженням Ember Tide, тож фанатам першої гри точно варто чекати.
"""),
    ("https://store.example/app/lantern-tide",
     "Lantern Tide on Store", "Kumo Forge", "2026-11-01", "official (store page)", """\
# Lantern Tide

Developer: Kumo Forge
Publisher: Kumo Forge
Release date: Mar 12, 2027
Platforms: Windows
Price: $24.99

Light the lanterns of a drowned city. Lantern Tide is a narrative exploration game about memory and the sea.
"""),
    ("https://forum.example/threads/kumo-forge-acquisition-memo.4412",
     "Leaked memo: MegaCorp acquiring Kumo Forge? | Gamefront Forums", "tidewatcher", "2026-11-03", "forum", """\
# Leaked memo: MegaCorp acquiring Kumo Forge?

tidewatcher, November 3, 2026
Leaked memo: MegaCorp is acquiring Kumo Forge, deal closes next month. Screenshot attached.

lampfan, November 3, 2026
That screenshot looks edited, the font is wrong.

tidewatcher, November 3, 2026
Believe what you want, it's real.
"""),
    ("https://social.example/kumoforge/status/88213",
     "Kumo Forge on Social", "Kumo Forge", "2026-11-04", "official (social)", """\
Kumo Forge, November 4, 2026

A fake "memo" about our studio being acquired is circulating. It is not real. Kumo Forge remains independent,
and Lantern Tide is still coming on March 12, 2027.
"""),
    ("https://tbt.example/articles/indie-budgets-2026",
     "Indie studios bet bigger in 2026 | Tokyo Business Times", "Kenji Arai", "2026-10-10", "press (paywalled fragment)", """\
[Fragment: only the part before the paywall was available.]

Indie studios bet bigger in 2026

By Kenji Arai, October 10, 2026

Budgets at Japan's independent studios are rising. Kumo Forge's budget for Lantern Tide is about 300 million yen,
according to people familiar with the matter. The studio declined to comment on the figure.
"""),
]

STATE = """\
# State

- Question: What is known about the indie game Lantern Tide by Kumo Forge: release, platforms, price, team, rumors?
- Text type / audience: short news explainer for a general gaming audience
- Phase: collected <!-- intake | plan proposed | plan approved | collecting Qn | assessed | drafting | ... -->
- Updated: 2026-11-10

## Settings

- Methodology: open
- User language: English
- Docs language: English
- Reads: en, ja, uk
- Translations: off <!-- auto | offer | off -->
- Rumors: {rumors} <!-- labeled | leads-only | exclude -->
- Depth: quick <!-- quick | standard | deep -->
- Limits: as of November 2026
- Wayback snapshots: off
- Citation style: footnotes <!-- footnotes | numbered | author-date -->
- Quotes: “” <!-- quotation marks; empty = by user language -->
- Common knowledge: off

## Decisions and user preferences

- Plan approved as is. Sources are collected; next: assess, then write the article.

## Done

- Sources S001-S011 saved and indexed (Rating and Origin not filled yet)

## Next

- Assess (claims, ratings, origins, log), then draft and final.md

## Gaps and open questions

-
"""

PLAN = """\
# Plan

Main question: What is known about Lantern Tide: release, platforms, price, team, rumors?

## Q1. Release date, platforms and price
- Languages: en (press), ja (Japanese studio and press)
- Status: collected

## Q2. Team and the game itself
- Languages: ja, en
- Status: collected

## Q3. Rumors and leaks
- Languages: ja (boards), en, uk (retellings)
- Status: collected
"""


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = sys.argv[1]
    rumors = os.environ.get("RUMORS", "labeled")
    os.makedirs(out)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (url, title, author, published, kind, text) in enumerate(SOURCES, 1):
            path = os.path.join(tmp, f"{i}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            capture = "user-paste" if "paywalled" in kind else "fixture"
            subprocess.run([sys.executable, FETCH, out, url, "--text-file", path, "--capture", capture,
                            "--title", title, "--no-archive", "--min-chars", "0"], check=True, capture_output=True)
            # fill what the Collect step fills: author, date, type
            index = os.path.join(out, "sources.md")
            with open(index, encoding="utf-8") as f:
                s = f.read()
            sid = f"S{i:03d}"
            head, _, rest = s.partition(f"## {sid} ")
            entry, sep, tail = rest.partition("\n## ")
            lang = "ja" if re.search(r"[\u3040-\u30ff]", text) else "uk" if re.search(r"[ієїґ]", text) else "en"
            entry = (entry.replace("- Language: \n", f"- Language: {lang}\n")
                          .replace("- Author: \n", f"- Author: {author}\n")
                          .replace("- Published: \n", f"- Published: {published}\n")
                          .replace("- Type: \n", f"- Type: {kind}\n"))
            with open(index, "w", encoding="utf-8") as f:
                f.write(head + f"## {sid} " + entry + sep + tail)
    for name, text in (("STATE.md", STATE.format(rumors=rumors)), ("plan.md", PLAN)):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(text)
    # claims.md, factcheck-log.md and draft.md are left for the agent to create (step 0 copies templates)
    print(f"built {out} (Rumors: {rumors})")
    write_reference_grader()


def write_reference_grader():
    """The no-invented-facts judge gets the full source texts, so its reference can't drift from the fixture."""
    texts = "\n\n".join(f"### Source {i}: {title} ({author}, {published})\n\n{text.strip()}"
                         for i, (url, title, author, published, kind, text) in enumerate(SOURCES, 1))
    body = f"""---
type: llm
focus:
  source: file
  path: research/lantern-tide/final.md
---

The article below is about the fictional game Lantern Tide. These are ALL of its sources, in full:

{texts}

Judge only substantive factual claims about the game, the studio, people, platforms, dates, prices, budget,
rumors and events. Ignore citations and footnotes (source titles, URLs, authors, access dates), formatting,
translation, harmless wording ("very quiet" for "quiet"), and the author's own analysis or conclusions.

PASS if every substantive factual claim in the article is supported by the sources above.
FAIL if the article states a substantive fact that no source supports (an invented date, platform, person,
number, feature, sale, review score, quote or event).
"""
    evals = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    for case in ("lantern-tide-open", "lantern-tide-exclude"):
        with open(os.path.join(evals, case, "graders", "no-invented-facts.md"), "w", encoding="utf-8") as f:
            f.write(body)


if __name__ == "__main__":
    main()
