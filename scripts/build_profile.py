"""Build the SVG blocks of the GitHub profile README (EN + RU).

    python3 scripts/build_profile.py

Writes assets/profile/*.svg and assets/profile/live.json. The daily workflow
(.github/workflows/profile.yml) runs the same command and commits only when the
output changes, so nothing here may depend on the build date.
"""

import base64
import io
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "scripts" / "profile" / "fonts"
OUT = ROOT / "assets" / "profile"
LIVE = OUT / "live.json"
USER = "m4rkellkka"
LANGS = ("en", "ru")


CONTENT = {
    "en": {
        "name": "Mikhail Savushkin",
        "place": "Istanbul",
        # (text, is_accent): the accent run stays on one line, set in italic with a hand-drawn underline.
        "headline": [("I build the apps a clinic's teams use", False), ("instead of", True), ("WhatsApp threads.", False)],
        "path": "Data Scientist at Yandex in 2022–23, then a clinic's sales team, now its full-stack engineer.",
        "open": "Open to full-stack and AI roles",
        "last_push": "last push",
        "private_repo": "a private project",
        "invite": [("Have a process that eats people's time?", False), ("Write to me.", True)],
        "stack": "Next.js · React · TypeScript · Postgres / Supabase · Node.js · LLM APIs · Python",
    },
    "ru": {
        "name": "Михаил Савушкин",
        "place": "Стамбул",
        "headline": [("Делаю приложения, которыми команды клиники пользуются", False), ("вместо", True), ("тредов в WhatsApp.", False)],
        "path": "Data Scientist в Яндексе в 2022–23, потом продажи в клинике, теперь её full-stack разработчик.",
        "open": "Открыт к full-stack и AI-ролям",
        "last_push": "последний пуш",
        "private_repo": "приватный проект",
        "invite": [("Есть процесс, который съедает время людей?", False), ("Напишите мне.", True)],
        "stack": "Next.js · React · TypeScript · Postgres / Supabase · Node.js · LLM APIs · Python",
    },
}

# README order. "live" marks a status that is real usage (accent dot) rather than a demo or side project.
PROJECTS = [
    {
        "slug": "tamam",
        "repo": None,
        # Private repos are matched by id, so their names never appear in this public repo.
        "repo_id": 1387651029,
        "title": "Tamam",
        "status": {"en": "in pilot", "ru": "в пилоте"},
        "live": True,
        "desc": {
            "en": "Requests and approvals instead of WhatsApp threads",
            "ru": "Заявки и согласования вместо тредов в WhatsApp",
        },
    },
    {
        "slug": "cv-screening",
        "repo": None,
        "repo_id": 1385646223,
        "title": "CV Screening",
        "status": {"en": "MVP demo", "ru": "демо MVP"},
        "live": False,
        "desc": {
            "en": "Rates each criterion with a quote from the CV; HR decides",
            "ru": "Оценивает каждый критерий цитатой из резюме, решает HR",
        },
    },
    {
        "slug": "whatsapp-qa",
        "repo": None,
        "title": "WhatsApp QA",
        "status": {"en": "in production", "ru": "в продакшене"},
        "live": True,
        "desc": {
            "en": "An LLM reads sales chats and points out what to fix",
            "ru": "LLM читает продажные чаты и подсказывает, что исправить",
        },
    },
    {
        "slug": "lumis",
        "repo": "Lumis",
        "title": "Lumis",
        "status": {"en": "side project", "ru": "пет-проект"},
        "live": False,
        "desc": {
            "en": "Exam prep on local LLMs; nothing leaves the laptop",
            "ru": "Подготовка к экзаменам на локальных LLM, всё остаётся на ноутбуке",
        },
    },
]


def oklch(l, c, h):
    """Convert an oklch() colour to #rrggbb."""
    a, b = c * math.cos(math.radians(h)), c * math.sin(math.radians(h))
    l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )

    def encode(x):
        x = min(max(x, 0.0), 1.0)
        x = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
        return round(x * 255)

    return "#" + "".join(f"{encode(x):02x}" for x in rgb)


# Same tokens as the :root blocks in index.html, so the profile and the resume site share one palette.
THEMES = {
    "light": {
        "paper": oklch(0.955, 0.012, 80),
        "ink": oklch(0.23, 0.012, 60),
        "soft": oklch(0.38, 0.012, 60),
        "muted": oklch(0.5, 0.016, 65),
        "accent": oklch(0.56, 0.155, 38),
        "line": "rgba(43,36,29,0.16)",
    },
    # GitHub dark is #0d1117: the hero card is warm graphite, the transparent rows use light ink.
    "dark": {
        "paper": oklch(0.21, 0.008, 60),
        "ink": oklch(0.93, 0.012, 80),
        "soft": oklch(0.83, 0.012, 80),
        "muted": oklch(0.76, 0.014, 72),
        "accent": oklch(0.72, 0.135, 42),
        "line": "rgba(240,233,222,0.16)",
    },
}


class Face:
    def __init__(self, family, filename):
        self.family = family
        self.path = FONTS / filename
        font = TTFont(self.path)
        self.cmap = font.getBestCmap()
        self.advance = font["hmtx"].metrics
        self.upm = font["head"].unitsPerEm
        self._cache = {}

    def width(self, text, size, spacing=0.0):
        units = sum(self.advance[self.cmap.get(ord(ch), ".notdef")][0] for ch in text)
        return units * size / self.upm + spacing * len(text)

    def woff2(self, chars):
        key = "".join(sorted(chars))
        if key not in self._cache:
            missing = sorted(ch for ch in chars if ord(ch) not in self.cmap)
            if missing:
                raise ValueError(f"{self.path.name} has no glyphs for {missing}")
            font = TTFont(self.path, recalcTimestamp=False)
            options = subset.Options()
            options.layout_features = ["kern", "liga", "calt", "locl"]
            subsetter = subset.Subsetter(options)
            subsetter.populate(text=key)
            subsetter.subset(font)
            font.flavor = "woff2"
            buffer = io.BytesIO()
            font.save(buffer)
            self._cache[key] = base64.b64encode(buffer.getvalue()).decode()
        return self._cache[key]


FACES = {
    face.family: face
    for face in (
        Face("pf-serif", "Literata-Display.ttf"),
        Face("pf-serif-it", "Literata-Display-Italic.ttf"),
        Face("pf-body", "Manrope-Regular.ttf"),
    )
}
SERIF, SERIF_IT, BODY = (FACES[k] for k in ("pf-serif", "pf-serif-it", "pf-body"))


def num(value):
    if isinstance(value, float):
        value = round(value, 2)
        return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip("0")
    return str(value)


def attrs(**values):
    # class_ -> class, stroke_width -> stroke-width; camelCase SMIL names pass through.
    return "".join(
        f' {name.rstrip("_").replace("_", "-")}="{escape(num(value), {chr(34): "&quot;"})}"'
        for name, value in values.items()
        if value is not None
    )


def el(tag, content=None, **values):
    if content is None:
        return f"<{tag}{attrs(**values)}/>"
    return f"<{tag}{attrs(**values)}>{content}</{tag}>"


class Svg:
    def __init__(self, width, height, title):
        self.width, self.height, self.title = width, height, title
        self.defs, self.body, self.styles = [], [], []
        self.chars = {}

    def add(self, *parts):
        self.body.extend(parts)

    def text(self, x, y, content, face, size, fill=None, **values):
        """content is a string or a list of (text, fill) or (text, fill, face) spans."""
        spans = [(content, None)] if isinstance(content, str) else content
        inner = ""
        for span in spans:
            part, span_fill = span[0], span[1]
            span_face = span[2] if len(span) > 2 else face
            self.chars.setdefault(span_face.family, set()).update(part)
            own_class = span_face.family if span_face is not face else None
            inner += el("tspan", escape(part), fill=span_fill, class_=own_class) if span_fill or own_class else escape(part)
        self.add(el("text", inner, x=x, y=y, class_=face.family, font_size=size, fill=fill, **values))

    def render(self):
        fonts = "".join(
            f"@font-face{{font-family:{family};src:url(data:font/woff2;base64,{FACES[family].woff2(chars)}) format('woff2')}}"
            f".{family}{{font-family:{family}}}"
            for family, chars in sorted(self.chars.items())
        )
        head = f'<svg xmlns="http://www.w3.org/2000/svg"{attrs(width=self.width, height=self.height, viewBox=f"0 0 {self.width} {self.height}", role="img")}>'
        style = "text{text-rendering:geometricPrecision;white-space:pre}" + fonts + "".join(self.styles)
        return "\n".join(
            [head, el("title", escape(self.title)), el("style", style), el("defs", "".join(self.defs)), *self.body, "</svg>\n"]
        )


def paper(svg, theme, radius=20):
    """A flat sheet of warm paper with a hairline edge: no grid, grain or glow."""
    c = THEMES[theme]
    svg.add(el("rect", x=0.5, y=0.5, width=svg.width - 1, height=svg.height - 1, rx=radius, fill=c["paper"], stroke=c["line"]))


def day_first(iso_date):
    """2026-09-10 -> 10.09.2026; live.json keeps ISO, only the rendered text flips."""
    year, month, day = iso_date.split("-")
    return f"{day}.{month}.{year}"


def fit(face, text, size, max_width, spacing=0.0):
    width = face.width(text, size, spacing)
    return size if width <= max_width else size * max_width / width


def greedy_lines(face, text, size, max_width):
    lines = []
    for word in text.split():
        trial = f"{lines[-1]} {word}" if lines else word
        if lines and face.width(trial, size) <= max_width:
            lines[-1] = trial
        else:
            lines.append(word)
    return lines


def wrap(face, text, size, max_width, max_lines):
    lines = greedy_lines(face, text, size, max_width)
    if len(lines) > max_lines:
        raise ValueError(f"{len(lines)} lines > {max_lines}: {text!r}")
    # Narrow the measure until the last line is at least half as long as the longest, so it is never a lone word.
    width = max_width

    def short_tail(candidate):
        return face.width(candidate[-1], size) < 0.5 * max(face.width(line, size) for line in candidate)

    while len(lines) > 1 and short_tail(lines):
        narrower = greedy_lines(face, text, size, width - 8)
        if len(narrower) > len(lines):
            break
        lines, width = narrower, width - 8
    return lines


def rich_lines(runs, size, max_width):
    """runs: [(text, is_accent)] -> lines of [(word, is_accent)]. An accent run is never split."""
    words = []
    for text, accent in runs:
        words += [(text, True)] if accent else [(w, False) for w in text.split()]
    lines, line, width = [], [], 0.0
    for word, accent in words:
        face = SERIF_IT if accent else SERIF
        add = face.width(word, size) + (SERIF.width(" ", size) if line else 0)
        if line and width + add > max_width:
            lines.append(line)
            line, width, add = [], 0.0, face.width(word, size)
        line.append((word, accent))
        width += add
    if line:
        lines.append(line)
    return lines


def balanced_lines(runs, size, max_width):
    """Like CSS text-wrap: balance: the narrowest measure that keeps the same number of lines."""
    lines = rich_lines(runs, size, max_width)
    width = max_width
    while width > max_width * 0.55:
        narrower = rich_lines(runs, size, width - 8)
        if len(narrower) > len(lines):
            break
        lines, width = narrower, width - 8
    return lines


def rich_text(svg, x, y, line, size, c):
    """Draw one line of (word, is_accent); return (start, end) x of the accent run, if any."""
    spans, cursor, accent_span = [], x, None
    for i, (word, accent) in enumerate(line):
        text = (" " if i else "") + word
        face = SERIF_IT if accent else SERIF
        if accent:
            start = cursor + (SERIF_IT.width(" ", size) if i else 0)
            accent_span = (start, cursor + face.width(text, size))
        spans.append((text, c["accent"] if accent else c["ink"], face))
        cursor += face.width(text, size)
    svg.text(x, y, spans, SERIF, size)
    return accent_span


def scribble(svg, start, end, y, c):
    """Hand-drawn underline that draws itself once when the image loads."""
    w = end - start
    d = (
        f"M{num(start)} {num(y)}C{num(start + w * 0.18)} {num(y - 3)} {num(start + w * 0.34)} {num(y + 2.6)} "
        f"{num(start + w * 0.52)} {num(y - 0.4)}S{num(start + w * 0.84)} {num(y - 2.6)} {num(end)} {num(y + 0.2)}"
    )
    svg.styles.append(
        # Visible by default: a renderer that skips CSS animation still shows the line.
        "@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}"
        ".scribble{stroke-dasharray:1;stroke-dashoffset:0;animation:draw .9s cubic-bezier(.65,0,.35,1) .5s both}"
        "@media (prefers-reduced-motion:reduce){.scribble{animation:none}}"
    )
    svg.add(el("path", d=d, pathLength=1, fill="none", stroke=c["accent"], stroke_width=2.6, stroke_linecap="round", class_="scribble"))


def hero(lang, theme, live):
    t, c = CONTENT[lang], THEMES[theme]
    pad, right, size, leading = 64, 1136, 50, 60
    lines = balanced_lines(t["headline"], size, right - pad)
    first = 168
    last = first + (len(lines) - 1) * leading
    path_y = last + 62
    rule_y = path_y + 40
    foot_y = rule_y + 42
    headline = " ".join(text for text, _ in t["headline"])
    svg = Svg(1200, foot_y + 38, f"{t['name']}. {headline}")
    paper(svg, theme)

    svg.text(pad, 78, t["name"], SERIF, 24, c["ink"])
    svg.text(right, 78, t["place"], BODY, 16, c["muted"], text_anchor="end")
    for i, line in enumerate(lines):
        y = first + i * leading
        accent = rich_text(svg, pad, y, line, size, c)
        if accent:
            scribble(svg, accent[0] - 2, accent[1] + 2, y + 13, c)
    for i, line in enumerate(wrap(BODY, t["path"], 19, right - pad, 2)):
        svg.text(pad, path_y + i * 28, line, BODY, 19, c["soft"])

    svg.add(el("path", d=f"M{pad} {rule_y}H{right}", stroke=c["line"]))
    svg.text(pad, foot_y, t["open"], BODY, 15, c["muted"])
    latest = live["latest"]
    title = latest["title"] or t["private_repo"]
    status = [(f"{t['last_push']} → ", c["muted"]), (title, c["ink"]), (f" · {day_first(latest['pushed'])}", c["muted"])]
    width = sum(BODY.width(part, 15) for part, _ in status)
    svg.add(el("circle", cx=num(right - width - 12), cy=foot_y - 5, r=3.5, fill=c["accent"]))
    svg.text(right, foot_y, status, BODY, 15, text_anchor="end")
    return svg


def work_row(project, index, lang, theme):
    """One line of the work list. Transparent, so consecutive rows read as one table of contents."""
    c = THEMES[theme]
    pad, right, h = 64, 1136, 116
    svg = Svg(1200, h, f"{project['title']} — {project['desc'][lang]} ({project['status'][lang]})")
    svg.text(pad, 66, f"0{index}", SERIF_IT, 30, c["accent"])
    svg.text(pad + 62, 60, project["title"], SERIF, 32, c["ink"])
    status = project["status"][lang]
    status_x = right - 26
    svg.text(num(status_x), 60, status, BODY, 15, c["muted"], text_anchor="end")
    dot_x = status_x - BODY.width(status, 15) - 12
    svg.add(el("circle", cx=num(dot_x), cy=55, r=3.5, fill=c["accent"] if project["live"] else c["line"]))
    ax, ay = right - 12, 48
    svg.add(el("path", d=f"M{ax} {ay + 12}L{ax + 12} {ay}M{ax + 3} {ay}H{ax + 12}V{ay + 9}", fill="none", stroke=c["muted"], stroke_width=1.6, stroke_linecap="round", stroke_linejoin="round"))
    desc = project["desc"][lang]
    svg.text(pad + 62, 92, desc, BODY, num(fit(BODY, desc, 18, right - pad - 62)), c["soft"])
    svg.add(el("path", d=f"M{pad} {h - 0.5}H{right}", stroke=c["line"]))
    return svg


def footer(lang, theme):
    t, c = CONTENT[lang], THEMES[theme]
    pad, right, size, leading = 64, 1136, 34, 44
    lines = balanced_lines(t["invite"], size, right - pad)
    first = 70
    stack_y = first + (len(lines) - 1) * leading + 46
    invite = " ".join(text for text, _ in t["invite"])
    svg = Svg(1200, stack_y + 30, f"{invite} {t['stack']}")
    for i, line in enumerate(lines):
        rich_text(svg, pad, first + i * leading, line, size, c)
    svg.text(pad, stack_y, t["stack"], BODY, 16, c["muted"])
    return svg


def fetch_live():
    # PROFILE_TOKEN (fine-grained, read-only metadata on my repos) lets private pushes count for "latest push".
    # Without it only public repos are visible: the workflow's GITHUB_TOKEN cannot see other repos.
    profile_token = os.environ.get("PROFILE_TOKEN")
    token = profile_token or os.environ.get("GITHUB_TOKEN")
    if profile_token:
        url = "https://api.github.com/user/repos?per_page=100&affiliation=owner"
    else:
        url = f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{USER}-profile-builder"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
            repos = json.load(response)
    except urllib.error.HTTPError as error:
        if profile_token and error.code == 401:
            # Fail the run so GitHub emails about it, instead of silently freezing the status.
            raise SystemExit("PROFILE_TOKEN was rejected, it has probably expired: create a new one and update the secret")
        print(f"GitHub API unavailable ({error}), using {LIVE.relative_to(ROOT)}")
        return json.loads(LIVE.read_text())
    except (OSError, ValueError) as error:
        print(f"GitHub API unavailable ({error}), using {LIVE.relative_to(ROOT)}")
        return json.loads(LIVE.read_text())

    # The profile repo itself is left out: every bot commit would change its push date and trigger another commit.
    repos = [r for r in repos if not r["fork"] and r["name"] != USER]
    latest = max(repos, key=lambda r: r["pushed_at"])
    if latest["private"]:
        # live.json is public: a private repo is named only by its card title, or not at all.
        title = next((p["title"] for p in PROJECTS if p.get("repo_id") == latest["id"]), None)
    else:
        title = next((p["title"] for p in PROJECTS if p["repo"] == latest["name"]), latest["name"])
    return {
        "latest": {"title": title, "pushed": latest["pushed_at"][:10]},
        "repos": {
            r["name"]: {"language": r["language"], "stars": r["stargazers_count"], "pushed": r["pushed_at"][:10]}
            for r in sorted(repos, key=lambda r: r["name"].lower())
            if not r["private"]
        },
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    live = fetch_live()
    LIVE.write_text(json.dumps(live, ensure_ascii=False, indent=2) + "\n")
    outputs = {}
    for lang in LANGS:
        for theme in THEMES:
            outputs[f"hero.{lang}.{theme}.svg"] = hero(lang, theme, live)
            for index, project in enumerate(PROJECTS, start=1):
                outputs[f"work-{project['slug']}.{lang}.{theme}.svg"] = work_row(project, index, lang, theme)
            outputs[f"footer.{lang}.{theme}.svg"] = footer(lang, theme)
    # Drop blocks that are no longer generated, so the folder always matches the README.
    for stale in OUT.glob("*.svg"):
        if stale.name not in outputs:
            stale.unlink()
    for name, svg in outputs.items():
        path = OUT / name
        path.write_text(svg.render())
        print(f"{name:36} {path.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
