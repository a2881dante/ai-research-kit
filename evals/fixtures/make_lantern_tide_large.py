#!/usr/bin/env python3
"""Build the large "Lantern Tide" research folder: the 11 core sources plus ~40 more, all long
like real web pages (navigation, related links, comments), so the whole set no longer fits in
one read.

  python3 evals/fixtures/make_lantern_tide_large.py <out_dir>

Also rewrites the no-invented-facts grader of the lantern-tide-large case.

Extra ground truth on top of make_lantern_tide.py:
  L1 release DELAYED to April 9, 2027        true   only in the Japanese official notice S012 (Nov 15, 2026);
                                                    ~15 reposts and the Nov 4 post still say March 12
  L2 Japan-only physical Switch 2 edition    true   S012; a forum post claims a worldwide physical edition (false)
  L3 PS5 rumor                               rumor  one origin, now retold by ~10 sites in several languages
  L4 Lantern Fall (Brightwick) on PS5, May 2027, and Tide Breakers: different games; nothing about them
                                                    applies to Lantern Tide
"""
import os
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_lantern_tide import FETCH, PLAN, SOURCES, STATE  # noqa: E402

R = random.Random(20261119)  # fixed seed: the fixture is identical on every build

DELAY_NOTICE = ("https://kumoforge.example/jp/news/lantern-tide-release-change",
                "『ランタン・タイド』発売日変更のお知らせ | 雲鍛冶スタジオ", "雲鍛冶スタジオ", "2026-11-15", "official", """\
# 『ランタン・タイド』発売日変更のお知らせ

2026年11月15日

いつも雲鍛冶スタジオをご支援いただき、誠にありがとうございます。

2027年3月12日に発売を予定しておりました『ランタン・タイド』（PC／Nintendo Switch 2）につきまして、
さらなる品質向上のため、発売日を2027年4月9日に変更させていただくことになりました。

楽しみにお待ちいただいている皆様には、心よりお詫び申し上げます。価格（24.99ドル）に変更はございません。
すでにご予約いただいた方は、そのまま新しい発売日にお届けします。

また、日本国内ではNintendo Switch 2向けのパッケージ版も発売いたします。海外でのパッケージ版の予定はございません。

雲鍛冶スタジオ ディレクター 村愛子
""")

OUTLETS = ["Pixel Ledger", "Joypad Times", "Save Point News", "Indie Lantern", "Frame Rate Daily",
           "GameScope", "Console Chronicle", "Respawn Report", "The Loading Screen", "Cartridge Weekly",
           "Next Level Wire", "Quest Log Magazine", "Boss Fight Bulletin", "Cozy Corner Games", "Patch Notes Today"]

REPOST_TEMPLATES = [
    "Kumo Forge has dated Lantern Tide: the narrative exploration game arrives on March 12, 2027 on PC and "
    "Nintendo Switch 2, priced at $24.99. Director Aiko Mura describes it as a story about a city that remembers. "
    "Pre-orders are open now.",
    "Lantern Tide, the drowned-city adventure from Kyoto studio Kumo Forge, is coming March 12, 2027. It will be "
    "available on Steam and Switch 2 for $24.99, the studio announced.",
    "Mark your calendars: Lantern Tide launches March 12, 2027. Kumo Forge's lamplighter game is headed to PC and "
    "Switch 2 at $24.99.",
]

PS5_REPOSTS = [
    ("en", "Lantern Tide reportedly heading to PS5 in 2028", "A PS5 version of Lantern Tide is reportedly planned for "
     "2028, according to a post on a Japanese message board first picked up by LeakHub. Kumo Forge has not commented."),
    ("en", "Is Lantern Tide coming to PlayStation?", "Rumors say Lantern Tide will come to PS5 in 2028. The claim "
     "started on a Japanese board and spread via LeakHub."),
    ("en", "PS5 owners may get Lantern Tide in 2028", "If LeakHub's report is right, Lantern Tide could land on PS5 "
     "in 2028. The original source is an anonymous message board post."),
    ("es", "Lantern Tide llegaría a PS5 en 2028", "Según un rumor publicado en un foro japonés y difundido por "
     "LeakHub, Lantern Tide llegaría a PS5 en 2028. Kumo Forge no lo ha confirmado."),
    ("ru", "Lantern Tide выйдет на PS5 в 2028 году?", "По слухам с японского форума, которые подхватил LeakHub, "
     "Lantern Tide выйдет на PS5 в 2028 году. Официального подтверждения нет."),
    ("uk", "Lantern Tide на PS5: що відомо", "LeakHub пише, що Lantern Tide вийде на PS5 у 2028 році. Джерело — "
     "анонімний допис на японському форумі."),
    ("en", "Lantern Tide PS5 port rumored", "Word is going around that Lantern Tide gets a PS5 port in 2028. Every "
     "report we found points back to LeakHub and a Japanese board post."),
    ("de", "Lantern Tide für PS5 im Jahr 2028?", "Laut einem Gerücht aus einem japanischen Forum, verbreitet von "
     "LeakHub, soll Lantern Tide 2028 für PS5 erscheinen. Kumo Forge schweigt dazu."),
]

OTHER_GAMES = [
    ("Lantern Fall gets a May 2027 date on PS5", "Brightwick Studios", "Brightwick Studios' action game Lantern Fall "
     "launches on May 20, 2027 on PS5 and Xbox Series X|S for $39.99. Director Paul Hendry promises a 30-hour "
     "campaign. Lantern Fall is a sequel to Ember Fall."),
    ("Lantern Fall preview: torches and swords", "Brightwick Studios", "Lantern Fall, Brightwick's follow-up to "
     "Ember Fall, has a soundtrack by composer Rita Okafor and a physical edition worldwide."),
    ("Tide Breakers announced for 2028", "Seawall Games", "Seawall Games announced Tide Breakers, a co-op sailing "
     "game coming in 2028 to PC, PS5 and Switch 2. The studio was acquired by MegaCorp last year."),
    ("Tide Breakers hands-on", "Seawall Games", "We played Tide Breakers for an hour. The game costs $29.99 and "
     "supports four-player co-op."),
    ("Ember Tide turns seven", "Hollow Pine", "Ember Tide, Hollow Pine's 2019 puzzle game, turns seven this year. "
     "The studio says a sequel is in development, without naming it."),
]

WORDS = ("the of and a to in is was for on that with as by at from this it game games studio players new year "
         "week release trailer update review story world city light sea design team music level map").split()
COMMENTS = ["Day one for me.", "Switch 2 version or nothing.", "Looks like Spiritfarer meets Gris.",
            "PS5 when?", "Heard it's coming to PS5 too, my cousin said so.", "$24.99 is fair.",
            "Wasn't this supposed to be PC only?", "The art style is gorgeous.", "Wishlisted.",
            "Is this a sequel to Ember Tide? Same vibe.", "Not a sequel, the director said so in an interview.",
            "Physical edition please!", "I think there will be a worldwide physical release.",
            "First!", "Does anyone know the composer?", "Kumo Forge got bought by MegaCorp, didn't they?",
            "No, that memo was fake.", "Delays happen, better than a broken launch."]


def filler(n):
    return " ".join(R.choice(WORDS) for _ in range(n)).capitalize() + "."


def page(outlet, title, body):
    """A web page as fetch.py would save it: navigation, the article, related links, comments, footer."""
    nav = "\n".join(f"- {x}" for x in ["Home", "News", "Reviews", "Previews", "Guides", "Hardware", "Deals",
                                        "Podcast", "Newsletter", "About", "Contact"])
    related = "\n".join(f"- {filler(R.randint(6, 10))}" for _ in range(8))
    paras = "\n\n".join(filler(R.randint(60, 120)) for _ in range(R.randint(14, 24)))
    comments = "\n\n".join(f"{R.choice(['lamp', 'tide', 'neon', 'kappa', 'mori', 'sora'])}{R.randint(1, 999)}: "
                           f"{R.choice(COMMENTS)}" for _ in range(R.randint(25, 60)))
    return (f"{outlet}\n\n{nav}\n\n# {title}\n\n{body}\n\n## More from {outlet}\n\n{paras}\n\n## Related\n\n"
            f"{related}\n\n## Comments\n\n{comments}\n\n© 2026 {outlet}. All rights reserved. Privacy | Terms | "
            f"Cookies | Advertise\n")


def sources():
    out = []
    for url, title, author, published, kind, text in SOURCES:  # press pages get page furniture like the rest
        if kind.startswith(("press", "aggregator", "blog")):
            outlet = title.rsplit("|", 1)[-1].strip()
            text = page(outlet, title.rsplit("|", 1)[0].strip(), text.split("\n", 1)[1].strip())
        out.append((url, title, author, published, kind, text))
    out.append(DELAY_NOTICE)
    out.append(("https://forum.example/threads/lantern-tide-physical.4520", "Lantern Tide physical edition? | "
                "Gamefront Forums", "boxcollector", "2026-11-16", "forum",
                "boxcollector, November 16, 2026\nLantern Tide is getting a physical edition worldwide, confirmed! "
                "Saw it on the Japanese site.\n\nlampfan, November 16, 2026\nThe Japanese notice says Japan only."))
    days = iter(range(16, 31))
    for i, outlet in enumerate(OUTLETS):
        slug = outlet.lower().replace(" ", "")
        out.append((f"https://{slug}.example/news/lantern-tide-date", f"Lantern Tide launches March 12, 2027 | {outlet}",
                    f"{outlet} staff", f"2026-09-{next(days, 30):02d}", "press (repost)",
                    page(outlet, "Lantern Tide launches March 12, 2027", REPOST_TEMPLATES[i % 3])))
    for i, (lang, title, body) in enumerate(PS5_REPOSTS):
        out.append((f"https://rumors{i + 1}.example/lantern-tide-ps5", f"{title} | Rumor Mill {i + 1}",
                    "staff", f"2026-10-{22 + i:02d}", "aggregator (repost)", page(f"Rumor Mill {i + 1}", title, body)))
    for i, (title, studio, body) in enumerate(OTHER_GAMES):
        outlet = OUTLETS[(i * 4) % len(OUTLETS)]
        out.append((f"https://{outlet.lower().replace(' ', '')}.example/news/other-{i + 1}", f"{title} | {outlet}",
                    f"{outlet} staff", f"2026-11-{5 + i:02d}", "press", page(outlet, title, body)))
    return out


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = sys.argv[1]
    os.makedirs(out)
    srcs = sources()
    order = list(range(len(srcs)))
    R.shuffle(order)  # the key sources sit somewhere in the middle, not first
    with tempfile.TemporaryDirectory() as tmp:
        for n, k in enumerate(order, 1):
            url, title, author, published, kind, text = srcs[k]
            path = os.path.join(tmp, f"{n}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            capture = "user-paste" if "paywalled" in kind else "fixture"
            subprocess.run([sys.executable, FETCH, out, url, "--text-file", path, "--capture", capture,
                            "--title", title, "--no-archive", "--min-chars", "0"], check=True, capture_output=True)
            index = os.path.join(out, "sources.md")
            with open(index, encoding="utf-8") as f:
                s = f.read()
            sid = f"S{n:03d}"
            head, _, rest = s.partition(f"## {sid} ")
            entry, sep, tail = rest.partition("\n## ")
            lang = ("ja" if any("぀" <= ch <= "ヿ" for ch in text) else
                    "uk" if any(ch in "ієїґ" for ch in text) else
                    "ru" if any("а" <= ch <= "я" for ch in text) else
                    "es" if " según " in text.lower() else "de" if " laut " in text.lower() else "en")
            entry = (entry.replace("- Language: \n", f"- Language: {lang}\n")
                          .replace("- Author: \n", f"- Author: {author}\n")
                          .replace("- Published: \n", f"- Published: {published}\n")
                          .replace("- Type: \n", f"- Type: {kind}\n"))
            with open(index, "w", encoding="utf-8") as f:
                f.write(head + f"## {sid} " + entry + sep + tail)
    state = STATE.format(rumors="labeled").replace("Depth: quick", "Depth: standard")
    for name, text in (("STATE.md", state), ("plan.md", PLAN)):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(text)
    words = sum(len(open(os.path.join(out, "sources", d, "original.md"), encoding="utf-8").read().split())
                for d in os.listdir(os.path.join(out, "sources")))
    print(f"built {out}: {len(srcs)} sources, ~{words} words")
    write_reference_grader(srcs)


def write_reference_grader(srcs):
    """The judge gets every article body, without page boilerplate and comments."""
    def body(text):
        if "## More from" in text:
            text = text.split("# ", 1)[1].split("## More from")[0]
        return text.strip()
    texts = "\n\n".join(f"### {title} ({author}, {published})\n\n{body(text)}"
                        for url, title, author, published, kind, text in srcs)
    grader = f"""---
type: llm
focus:
  source: file
  path: research/lantern-tide/final.md
---

The article below is about the fictional game Lantern Tide. These are the article bodies of ALL its sources
(page navigation and reader comments omitted). Some sources are about OTHER games (Lantern Fall, Tide Breakers,
Ember Tide); their facts do not apply to Lantern Tide.

{texts}

Judge only substantive factual claims about Lantern Tide, its studio Kumo Forge, people, platforms, dates,
prices, editions, budget, rumors and events. Ignore citations and footnotes (titles, URLs, authors, access
dates), formatting, translation, harmless wording, and the author's own analysis.

PASS if every substantive factual claim is supported by a source above and attributed to the right game.
FAIL if the article states a fact no source supports, or applies a fact about another game to Lantern Tide.
"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lantern-tide-large", "graders",
                        "no-invented-facts.md")
    if os.path.isdir(os.path.dirname(path)):
        with open(path, "w", encoding="utf-8") as f:
            f.write(grader)


if __name__ == "__main__":
    main()
