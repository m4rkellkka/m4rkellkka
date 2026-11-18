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
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "scripts" / "profile" / "fonts"
OUT = ROOT / "assets" / "profile"
LIVE = OUT / "live.json"
CONTRIB = OUT / "contributions.json"
USER = "m4rkellkka"
LANGS = ("en", "ru")


CONTENT = {
    "en": {
        "name": "Mikhail Savushkin",
        "place": "Istanbul",
        "caption": "Istanbul, 2026",
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
        "caption": "Стамбул, 2026",
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
        "visual": {
            "en": {"rows": [("#1042", "Control visit", "Waiting for manager", True), ("#1041", "Hotel change", "With coordinator", False), ("#1039", "Consultation", "Done", False)]},
            "ru": {"rows": [("#1042", "Контроль", "Ждёт менеджера", True), ("#1041", "Смена отеля", "У координатора", False), ("#1039", "Консультация", "Выполнена", False)]},
        },
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
        "visual": {
            "en": {"criterion": "Sales experience", "score": "4 / 5", "quote": "“Two years selling to international clients”", "note": "Score computed in code · personal data removed"},
            "ru": {"criterion": "Опыт продаж", "score": "4 / 5", "quote": "«Два года продаж иностранным клиентам»", "note": "Балл считает код · персональные данные убраны"},
        },
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
        "visual": {
            "en": {"chat": [("client", "Is this the final price?"), ("seller", "Yes")], "flag": "No next step offered: suggest a consultation"},
            "ru": {"chat": [("client", "Это окончательная цена?"), ("seller", "Да")], "flag": "Нет следующего шага: предложить консультацию"},
        },
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
        "visual": {
            "en": {"question": "What does spaced repetition optimise?", "hint": "Card 12 of 40 · written by a local LLM"},
            "ru": {"question": "Что оптимизирует интервальное повторение?", "hint": "Карточка 12 из 40 · написана локальной LLM"},
        },
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
# One dark palette for both GitHub themes: near-black (not brown), warm ink, a single terracotta accent.
C = {
    "bg": oklch(0.16, 0.004, 60),
    "raised": oklch(0.205, 0.006, 60),
    "ink": oklch(0.94, 0.01, 80),
    "soft": oklch(0.82, 0.012, 78),
    "muted": oklch(0.66, 0.014, 72),
    "accent": oklch(0.68, 0.155, 40),
    "line": "rgba(255,255,255,0.09)",
    "line_strong": "rgba(255,255,255,0.16)",
}
PHOTO = Path(__file__).resolve().parent / "profile" / "photo.jpg"


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
        Face("pf-mono", "JetBrainsMono-Regular.ttf"),
    )
}
SERIF, SERIF_IT, BODY, MONO = (FACES[k] for k in ("pf-serif", "pf-serif-it", "pf-body", "pf-mono"))


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
        extra = values.pop("class_", None)  # e.g. an animation class next to the font class
        css = f"{face.family} {extra}" if extra else face.family
        self.add(el("text", inner, x=x, y=y, class_=css, font_size=size, fill=fill, **values))

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


def backdrop(svg, radius=18, glow=None):
    """Flat near-black card, hairline edge, at most one soft terracotta glow. No grid, no grain."""
    w, h = svg.width, svg.height
    svg.defs.append(el("clipPath", el("rect", width=w, height=h, rx=radius), id="frame"))
    layers = el("rect", width=w, height=h, fill=C["bg"])
    if glow:
        cx, cy, r = glow
        svg.defs.append(
            el(
                "radialGradient",
                el("stop", offset=0, stop_color=C["accent"], stop_opacity=0.08) + el("stop", offset=1, stop_color=C["accent"], stop_opacity=0),
                id="glow", cx=cx, cy=cy, r=r,
            )
        )
        layers += el("rect", width=w, height=h, fill="url(#glow)")
    svg.add(el("g", layers, clip_path="url(#frame)"))
    svg.add(el("rect", x=0.5, y=0.5, width=w - 1, height=h - 1, rx=radius - 0.5, fill="none", stroke=C["line_strong"]))


def pill(svg, right, y, label, size, accent=False):
    """Status pill anchored by its right edge; returns its left x."""
    w = BODY.width(label, size) + 22
    svg.add(el("rect", x=num(right - w), y=num(y - size - 2), width=num(w), height=num(size + 13), rx=num((size + 13) / 2),
               fill=C["accent"] if accent else "#ffffff", fill_opacity=0.16 if accent else 0.06))
    svg.text(num(right - 11), num(y + 1), label, BODY, size, C["accent"] if accent else C["soft"], text_anchor="end")
    return right - w


def hero(lang, live):
    t = CONTENT[lang]
    pad, size, leading = 64, 54, 64
    text_right = 820
    lines = balanced_lines(t["headline"], size, text_right - pad)
    first = 176
    last = first + (len(lines) - 1) * leading
    path_lines = wrap(BODY, t["path"], 19, text_right - pad, 2)
    path_y = last + 58
    rule_y = max(path_y + (len(path_lines) - 1) * 28 + 44, 420)
    foot_y = rule_y + 42
    headline = " ".join(text for text, _ in t["headline"])
    svg = Svg(1200, foot_y + 38, f"{t['name']}. {headline}")
    backdrop(svg, glow=(0.12, 0.0, 0.7))
    svg.styles.append(
        "@keyframes ping{0%{transform:scale(1);opacity:.7}80%,100%{transform:scale(2.6);opacity:0}}"
        ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.4s cubic-bezier(0,0,.2,1) infinite}"
        "@media (prefers-reduced-motion:reduce){.ping{animation:none;opacity:0}}"
    )

    svg.text(pad, 82, t["name"], SERIF, 24, C["ink"])
    svg.text(pad + SERIF.width(t["name"], 24) + 14, 82, f"· {t['place']}", BODY, 16, C["muted"])
    for i, line in enumerate(lines):
        y = first + i * leading
        accent = rich_text(svg, pad, y, line, size, C)
        if accent:
            scribble(svg, accent[0] - 2, accent[1] + 2, y + 13, C)
    for i, line in enumerate(path_lines):
        svg.text(pad, path_y + i * 28, line, BODY, 19, C["soft"])

    # The photo as a print, tilted, like on the resume site.
    fx, fy, fw, fh = 900, 58, 236, 336
    photo = base64.b64encode(PHOTO.read_bytes()).decode()
    svg.defs.append(el("filter", el("feDropShadow", dx=0, dy=14, stdDeviation=14, flood_color="#000", flood_opacity=0.5), id="lift", x="-30%", y="-30%", width="160%", height="160%"))
    print_ = (
        el("rect", x=fx, y=fy, width=fw, height=fh, fill="#f6f2ea", filter="url(#lift)")
        + el("image", x=fx + 10, y=fy + 10, width=fw - 20, height=num((fw - 20) * 4 / 3), href=f"data:image/jpeg;base64,{photo}", preserveAspectRatio="xMidYMid slice")
    )
    svg.add(el("g", print_, transform=f"rotate(3 {fx + fw / 2} {fy + fh / 2})"))
    svg.text(num(fx + fw / 2), fy + fh - 16, t["caption"], SERIF_IT, 17, "#5a534b", text_anchor="middle", transform=f"rotate(3 {fx + fw / 2} {fy + fh / 2})")

    svg.add(el("path", d=f"M{pad} {rule_y}H1136", stroke=C["line"]))
    svg.text(pad, foot_y, t["open"], BODY, 15, C["muted"])
    latest = live["latest"]
    title = latest["title"] or t["private_repo"]
    status = [(f"{t['last_push']} → ", C["muted"]), (title, C["ink"]), (f" · {day_first(latest['pushed'])}", C["muted"])]
    width = sum(BODY.width(part, 15) for part, _ in status)
    dot_x = 1136 - width - 14
    svg.add(el("circle", cx=num(dot_x), cy=foot_y - 5, r=4, fill=C["accent"], class_="ping"), el("circle", cx=num(dot_x), cy=foot_y - 5, r=4, fill=C["accent"]))
    svg.text(1136, foot_y, status, BODY, 15, text_anchor="end")
    return svg


def visual_tamam(svg, x, y, w, v):
    for i, (rid, kind, status, waiting) in enumerate(v["rows"]):
        ry = y + 36 + i * 44
        if i:
            svg.add(el("path", d=f"M{x + 16} {ry - 29}H{x + w - 16}", stroke=C["line"]))
        svg.text(x + 16, ry, rid, BODY, 15, C["muted"])
        svg.text(x + 76, ry, kind, BODY, 17, C["ink"])
        pill(svg, x + w - 16, ry, status, 14, accent=waiting)


def visual_cv(svg, x, y, w, v):
    svg.text(x + 18, y + 34, v["criterion"], BODY, 17, C["ink"])
    svg.text(x + w - 18, y + 34, v["score"], BODY, 17, C["accent"], text_anchor="end")
    bar_w = w - 36
    svg.add(
        el("rect", x=x + 18, y=y + 48, width=bar_w, height=6, rx=3, fill="#ffffff", fill_opacity=0.08),
        el("rect", x=x + 18, y=y + 48, width=num(bar_w * 0.8), height=6, rx=3, fill=C["accent"]),
        el("path", d=f"M{x + 18} {y + 76}V{y + 104}", stroke=C["accent"], stroke_width=2),
    )
    svg.text(x + 30, y + 96, v["quote"], SERIF_IT, num(fit(SERIF_IT, v["quote"], 18, w - 48)), C["soft"])
    svg.text(x + 18, y + 128, v["note"], BODY, 14, C["muted"])


def visual_qa(svg, x, y, w, v):
    (who1, msg1), (who2, msg2) = v["chat"]
    b1 = BODY.width(msg1, 16) + 28
    svg.add(el("rect", x=x + 16, y=y + 14, width=num(b1), height=34, rx=14, fill="#ffffff", fill_opacity=0.07))
    svg.text(x + 30, y + 36, msg1, BODY, 16, C["soft"])
    b2 = BODY.width(msg2, 16) + 28
    svg.add(el("rect", x=num(x + w - 16 - b2), y=y + 56, width=num(b2), height=34, rx=14, fill=C["accent"], fill_opacity=0.18))
    svg.text(num(x + w - 30), y + 78, msg2, BODY, 16, C["ink"], text_anchor="end")
    svg.add(el("circle", cx=x + 22, cy=y + 117, r=4, fill=C["accent"]))
    svg.text(x + 34, y + 122, v["flag"], BODY, 15, C["accent"])


def visual_lumis(svg, x, y, w, v):
    svg.add(
        el("rect", x=x + 26, y=y + 22, width=w - 52, height=78, rx=10, fill="#ffffff", fill_opacity=0.04, stroke=C["line"], transform=f"rotate(-2 {x + w / 2} {y + 61})"),
        el("rect", x=x + 18, y=y + 16, width=w - 36, height=82, rx=10, fill=C["raised"], stroke=C["line_strong"]),
    )
    svg.text(x + 34, y + 50, v["question"], SERIF, num(fit(SERIF, v["question"], 18, w - 68)), C["ink"])
    svg.text(x + 34, y + 80, v["hint"], BODY, 14, C["muted"])
    track = w - 36
    svg.add(
        el("rect", x=x + 18, y=y + 116, width=track, height=6, rx=3, fill="#ffffff", fill_opacity=0.08),
        el("rect", x=x + 18, y=y + 116, width=num(track * 0.3), height=6, rx=3, fill=C["accent"]),
    )


VISUALS = {"tamam": visual_tamam, "cv-screening": visual_cv, "whatsapp-qa": visual_qa, "lumis": visual_lumis}


def card(project, index, lang):
    w, h, pad = 600, 388, 34
    svg = Svg(w, h, f"{project['title']} — {project['desc'][lang]} ({project['status'][lang]})")
    backdrop(svg, 16)
    svg.text(pad, 60, f"0{index}", SERIF_IT, 28, C["accent"])
    status = project["status"][lang]
    svg.text(w - pad, 56, status, BODY, 15, C["muted"], text_anchor="end")
    svg.add(el("circle", cx=num(w - pad - BODY.width(status, 15) - 12), cy=51, r=4, fill=C["accent"] if project["live"] else C["line_strong"]))
    svg.text(pad, 106, project["title"], SERIF, num(fit(SERIF, project["title"], 34, w - 2 * pad)), C["ink"])
    for i, line in enumerate(wrap(BODY, project["desc"][lang], 18, w - 2 * pad, 2)):
        svg.text(pad, 142 + i * 26, line, BODY, 18, C["soft"])
    bx, by, bw, bh = pad, 206, w - 2 * pad, 148
    svg.add(el("rect", x=bx, y=by, width=bw, height=bh, rx=12, fill=C["raised"], stroke=C["line"]))
    VISUALS[project["slug"]](svg, bx, by, bw, project["visual"][lang])
    return svg


def footer(lang):
    t = CONTENT[lang]
    pad, right, size, leading = 64, 1136, 34, 44
    lines = balanced_lines(t["invite"], size, right - pad)
    first = 82
    stack_y = first + (len(lines) - 1) * leading + 50
    invite = " ".join(text for text, _ in t["invite"])
    svg = Svg(1200, stack_y + 46, f"{invite} {t['stack']}")
    backdrop(svg, glow=(0.9, 1.0, 0.7))
    for i, line in enumerate(lines):
        accent = rich_text(svg, pad, first + i * leading, line, size, C)
    svg.text(pad, stack_y, t["stack"], BODY, 16, C["muted"])
    return svg


GRAPH_TEXT = {
    "en": {
        "total": "contributions in the last year",
        "longest": "longest streak",
        "current": "current streak",
        "days": "days",
        "busiest": "busiest day: {count}, {date}",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "city": "A year of commits, as a skyline over the Bosphorus",
        "city_note": "each building is a week · lit windows are contributions",
        "busiest_week": "busiest week",
    },
    "ru": {
        "total": "контрибуций за последний год",
        "longest": "самая длинная серия",
        "current": "текущая серия",
        "days": "дн.",
        "busiest": "самый плотный день: {count}, {date}",
        "months": ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
        "city": "Год коммитов — силуэт города над Босфором",
        "city_note": "каждое здание — неделя · горящие окна — контрибуции",
        "busiest_week": "самая плотная неделя",
    },
}


def contribution_stats(days):
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    tail = counts[:-1] if counts and counts[-1] == 0 else counts  # today may simply not have started yet
    for c in reversed(tail):
        if not c:
            break
        current += 1
    busiest = max(range(len(days)), key=lambda i: (days[i][1], i))
    return {"longest": longest, "current": current, "busiest": busiest}


def grouped(n, lang):
    return f"{n:,}".replace(",", " " if lang == "ru" else ",")


def contribution_graph(lang, contrib):
    """The contribution calendar inked in week by week, with a hand-written note on the busiest day."""
    t = GRAPH_TEXT[lang]
    days = contrib["days"]
    stats = contribution_stats(days)
    # GitHub weeks start on Sunday; pad the first week so rows are weekdays.
    first = date.fromisoformat(days[0][0])
    offset = (first.weekday() + 1) % 7
    cells = [(offset + i) for i in range(len(days))]
    weeks = (cells[-1] // 7) + 1
    step, size = 20, 16
    x0 = (1200 - weeks * step) // 2 + 2
    y0 = 214
    nonzero = sorted(c for _, c in days if c)
    q = [nonzero[int(len(nonzero) * p)] if nonzero else 1 for p in (0.25, 0.5, 0.75)]

    def level(c):
        return 0 if not c else 1 + sum(c > v for v in q)

    svg = Svg(1200, 404, f"{grouped(contrib['total'], lang)} {t['total']}")
    backdrop(svg)
    svg.styles.append(
        "@keyframes ink{from{opacity:0;transform:translateY(5px)}}"
        ".wk{animation:ink .6s cubic-bezier(.2,.7,.2,1) both}"
        "@keyframes show{from{opacity:0}}.late{animation:show .6s ease 1.7s both}"
        "@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}"
        ".arrow{stroke-dasharray:1;animation:draw .8s cubic-bezier(.65,0,.35,1) 1.5s both}"
        "@keyframes ping{0%{transform:scale(1);opacity:.8}80%,100%{transform:scale(2.2);opacity:0}}"
        ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.4s cubic-bezier(0,0,.2,1) 2s infinite both}"
        "@keyframes blink{0%,91%,100%{opacity:1}93%,97%{opacity:0}}.eo{animation:blink 4.6s infinite}"
        "@keyframes blinkc{0%,91%,100%{opacity:0}93%,97%{opacity:1}}.ec{animation:blinkc 4.6s infinite}"
        ".cat-still{display:none}"
        "@media (prefers-reduced-motion:reduce){.wk,.late,.arrow,.ping,.eo,.ec{animation:none}.ping,.ec{opacity:0}.cat{display:none}.cat-still{display:inline}}"
    )

    total = grouped(contrib["total"], lang)
    svg.text(64, 106, total, SERIF, 58, C["ink"])
    svg.text(64 + SERIF.width(total, 58) + 16, 104, t["total"], BODY, 19, C["soft"])
    for i, (label, value) in enumerate(((t["longest"], stats["longest"]), (t["current"], stats["current"]))):
        y = 78 + i * 28
        svg.text(1136, y, [(f"{label}  ", C["muted"]), (f"{value} {t['days']}", C["ink"])], BODY, 16, text_anchor="end")

    fills = ["#ffffff", C["accent"], C["accent"], C["accent"], C["accent"]]
    opacity = [0.06, 0.3, 0.55, 0.8, 1]
    for week in range(weeks):
        rects = ""
        for i, cell in enumerate(cells):
            if cell // 7 != week:
                continue
            lv = level(days[i][1])
            rects += el("rect", x=x0 + week * step, y=y0 + (cell % 7) * step, width=size, height=size, rx=4, fill=fills[lv], fill_opacity=opacity[lv])
        svg.add(el("g", rects, class_="wk", style=f"animation-delay:{week * 26}ms"))

    # Month names under the first column that starts a new month.
    seen = set()
    for i, (iso, _) in enumerate(days):
        d = date.fromisoformat(iso)
        week = cells[i] // 7
        if d.day <= 7 and (d.year, d.month) not in seen and week < weeks - 1:
            seen.add((d.year, d.month))
            svg.text(x0 + week * step, y0 + 7 * step + 22, t["months"][d.month - 1], BODY, 13, C["muted"])

    # Today: a ring that keeps breathing.
    today = cells[-1]
    tx, ty = x0 + (today // 7) * step + size / 2, y0 + (today % 7) * step + size / 2
    svg.add(el("rect", x=num(tx - 11), y=num(ty - 11), width=22, height=22, rx=7, fill="none", stroke=C["accent"], stroke_width=1.5, class_="ping"))

    # Hand-written note with a curved arrow to the busiest day.
    b = stats["busiest"]
    bd = date.fromisoformat(days[b][0])
    bx, by = x0 + (cells[b] // 7) * step + size / 2, y0 + (cells[b] % 7) * step
    note = t["busiest"].format(count=days[b][1], date=f"{bd.day} {t['months'][bd.month - 1]}")
    note_w = SERIF_IT.width(note, 19)
    right_side = bx < 600
    nx = bx + 34 if right_side else bx - 34 - note_w
    ny = 174
    sx = nx - 8 if right_side else nx + note_w + 8
    svg.text(num(nx), ny, note, SERIF_IT, 19, C["soft"], class_="late")
    d = f"M{num(sx)} {ny - 6}C{num(bx + (sx - bx) * 0.35)} {ny - 8} {num(bx)} {ny + 2} {num(bx)} {num(by - 6)}"
    svg.add(
        el("path", d=d, pathLength=1, fill="none", stroke=C["accent"], stroke_width=1.6, stroke_linecap="round", class_="arrow"),
        el("path", d=f"M{num(bx - 4)} {num(by - 11)}L{num(bx)} {num(by - 5)}L{num(bx + 4)} {num(by - 11)}", fill="none", stroke=C["accent"], stroke_width=1.6, stroke_linecap="round", stroke_linejoin="round", class_="late"),
    )

    return svg


# The cat from way-to-1111 as pixel art made of ASCII: every pixel is a square cell in its colour
# with a glyph of the same hue on top, picked by brightness like the game picks its glyphs.
# Bodies are drawn as left halves (the centre column last) and mirrored; tails are added after.
CAT_HEAD = [
    "..KK......",
    "..KOK.....",
    "..KOPK....",
    ".KOOPOKKKK",
    ".KOOOOOOOO",
    ".KOTOOOTOO",
    ".KOOOOOOOO",
    ".KOKGGKOOO",
    ".KOKGkKOOO",
    ".KLOKKOOWP",
    ".KLLOOWWWK",
    "..KLOOWWWW",
]
CAT_HEAD_ASLEEP = CAT_HEAD[:7] + [".KOOOOOOOO", ".KOKKKOOOO"] + CAT_HEAD[9:]
CAT_BODIES = {
    "sit": [
        "..KOOOOWWW",
        ".KOOTOOWWW",
        ".KOOOTOWWW",
        ".KOTOOOWWW",
        ".KOOOTOOWW",
        ".KOOOOKWWW",
        ".KOOOOKWWW",
        ".KOOOKWWWK",
        "..KKKKKKKK",
    ],
    "jump": [
        "..KOOOOWWW",
        ".KOOTOOWWW",
        "KOOOOTOWWW",
        "KOOTOOOWWW",
        ".KOOOOOWWW",
        "..KOKKOOKK",
        "..KWK.KWK.",
        "..KWK.KWK.",
        "...K...K..",
    ],
    "sleep": [
        ".KOOOOOWWW",
        "KOOTOOOOWW",
        "KOOOTOOOOO",
        "KOOOOOOOOO",
        ".KKKKKKKKK",
    ],
}
# (row from the top, column, colour) added to the right of the 19-wide body
CAT_TAILS = {
    "sit": [(16, 19, "K"), (17, 19, "O"), (17, 20, "K"), (18, 19, "O"), (18, 20, "D"), (18, 21, "K"),
            (19, 18, "O"), (19, 19, "O"), (19, 20, "D"), (19, 21, "K"), (20, 17, "K"), (20, 18, "K"), (20, 19, "K"), (20, 20, "K")],
    "jump": [(12, 19, "K"), (12, 20, "K"), (13, 18, "O"), (13, 19, "O"), (13, 20, "D"), (13, 21, "K"),
             (14, 18, "O"), (14, 19, "K"), (11, 20, "K"), (11, 21, "D"), (10, 21, "K"), (10, 22, "K")],
    "sleep": [(14, 19, "O"), (14, 20, "D"), (14, 21, "K"), (15, 19, "O"), (15, 20, "O"), (15, 21, "K"), (16, 18, "K"), (16, 19, "K"), (16, 20, "K")],
}
CAT_PALETTE = {
    "K": ("#2b1b12", ":"), "D": ("#7a3f1b", "="), "O": ("#c96d2e", "+"), "L": ("#e89552", "*"),
    "T": ("#9c4f20", "="), "W": ("#f2e4cf", "#"), "P": ("#e98e8e", "o"), "G": ("#9ccf6a", "O"), "k": ("#10100e", "."),
}


def lighten(hex_colour, amount=0.32):
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(v + (255 - v) * amount):02x}" for v in (r, g, b))


def cat_pixels(pose):
    head = CAT_HEAD_ASLEEP if pose == "sleep" else CAT_HEAD
    rows = [half + half[-2::-1] for half in head + CAT_BODIES[pose]]
    grid = [list(row.ljust(24, ".")) for row in rows]
    for r, c, colour in CAT_TAILS[pose]:
        while r >= len(grid):
            grid.append(list("." * 24))
        grid[r][c] = colour
    return grid


def cat_sprite(svg, pose, cell=3.6):
    """Pixel-art cat anchored at its bottom centre (0, 0) of the 19-wide body."""
    grid = cat_pixels(pose)
    left, top = -9.5 * cell, -len(grid) * cell
    paths, texts = {}, {}
    for r, row in enumerate(grid):
        for c, colour in enumerate(row):
            if colour == ".":
                continue
            x, y = left + c * cell, top + r * cell
            paths.setdefault(colour, []).append(f"M{num(x)} {num(y)}h{num(cell)}v{num(cell)}h{num(-cell)}z")
    out = "".join(el("path", d="".join(d), fill=CAT_PALETTE[k][0]) for k, d in paths.items())
    size = cell / 0.6  # JetBrains Mono advance is 0.6 em, so one glyph per pixel
    glyph_rows = ""
    for r, row in enumerate(grid):
        spans, prev = [], None
        for colour in row:
            glyph, fill = (" ", None) if colour == "." else (CAT_PALETTE[colour][1], lighten(CAT_PALETTE[colour][0]))
            if spans and fill == prev:
                spans[-1][0] += glyph
            else:
                spans.append([glyph, fill])
                prev = fill
        text = "".join(t for t, _ in spans)
        if not text.strip():
            continue
        svg.chars.setdefault(MONO.family, set()).update(text)
        inner = "".join(el("tspan", escape(t), fill=f) if f else escape(t) for t, f in spans)
        glyph_rows += el("text", inner, x=num(left), y=num(top + r * cell + cell * 0.82), class_=MONO.family, font_size=num(size), fill_opacity=0.55)
    return out + glyph_rows


def quad_length(p0, c, p1, steps=16):
    total, prev = 0.0, p0
    for i in range(1, steps + 1):
        t = i / steps
        pt = ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])
        total += math.hypot(pt[0] - prev[0], pt[1] - prev[1])
        prev = pt
    return total


def roof_cat(svg, roofs, totals):
    """The cat hops along the roofs, sits for a moment on each stop and sleeps through long quiet spells."""
    stops, w = [], 0
    while w < len(totals):
        if totals[w] == 0:
            j = w
            while j < len(totals) and totals[j] == 0:
                j += 1
            if j - w >= 4:
                stops.append(((w + j) // 2, "sleep"))
            w = j
            continue
        stops.append((w, "sit"))
        w += 4 + (w * 7) % 3
    route = stops + stops[-2::-1]
    events = [(0.0, 0.0)]  # (time, distance along the path)
    segments = []  # (start time, pose, facing)
    path = f"M{num(roofs[route[0][0]][0])} {num(roofs[route[0][0]][1])}"
    t = d = 0.0
    for k, (week, pose) in enumerate(route):
        nxt = route[k + 1][0] if k + 1 < len(route) else None
        facing = "r" if nxt is None or roofs[nxt][0] >= roofs[week][0] else "l"
        segments.append((t, pose, "r" if pose == "sleep" else facing))
        t += 7.0 if pose == "sleep" else 2.4
        events.append((t, d))
        if nxt is None:
            break
        (x1, y1), (x2, y2) = roofs[week], roofs[nxt]
        c = ((x1 + x2) / 2, min(y1, y2) - 44 - 0.12 * abs(x2 - x1))
        path += f"Q{num(c[0])} {num(c[1])} {num(x2)} {num(y2)}"
        segments.append((t, "jump", facing))
        t += 0.55 + abs(x2 - x1) / 700
        d += quad_length((x1, y1), c, (x2, y2))
        events.append((t, d))
    total_t, total_d = t, d or 1
    key_times = ";".join(num(round(e[0] / total_t, 4)) for e in events)
    key_points = ";".join(num(round(e[1] / total_d, 4)) for e in events)
    motion = el("animateMotion", path=path, dur=f"{num(round(total_t, 2))}s", keyTimes=key_times, keyPoints=key_points, calcMode="linear", repeatCount="indefinite")

    times = ";".join(num(round(s[0] / total_t, 4)) for s in segments)
    groups = ""
    for pose, facing in (("sit", "r"), ("sit", "l"), ("jump", "r"), ("jump", "l"), ("sleep", "r")):
        values = ";".join("1" if (s[1], s[2]) == (pose, facing) else "0" for s in segments)
        show = el("animate", attributeName="opacity", values=values, keyTimes=times, dur=f"{num(round(total_t, 2))}s", calcMode="discrete", repeatCount="indefinite")
        art = cat_sprite(svg, pose)
        if pose == "sleep":
            svg.chars.setdefault(SERIF_IT.family, set()).update("zZ")
            art += el("text", "z", x=30, y=-62, class_=f"{SERIF_IT.family} zz", font_size=10, fill=C["soft"])
            art += el("text", "Z", x=40, y=-76, class_=f"{SERIF_IT.family} zz z2", font_size=13, fill=C["soft"])
        flip = ' transform="scale(-1 1)"' if facing == "l" else ""
        groups += f"<g opacity=\"0\"{flip}>{show}{art}</g>"
    svg.styles.append(
        "@keyframes zz{0%{opacity:0;transform:translate(0,4px)}30%{opacity:.9}100%{opacity:0;transform:translate(6px,-10px)}}"
        ".zz{animation:zz 2.6s ease-out infinite}.z2{animation-delay:1.3s}"
        ".cat-still{display:none}"
        "@media (prefers-reduced-motion:reduce){.cat{display:none}.cat-still{display:inline}.zz{animation:none}}"
    )
    svg.add(el("g", groups + motion, class_="cat"))
    first = roofs[stops[0][0]]
    svg.add(el("g", cat_sprite(svg, "sit"), transform=f"translate({num(first[0])} {num(first[1])})", class_="cat-still"))


def window_lit(week, row, col, pct):
    # Stable pseudo-random pattern: the same data always lights the same windows.
    return (week * 7919 + row * 104729 + col * 1299709) % 100 < pct


def skyline(lang, contrib):
    """Weekly totals as buildings over the water: height and lit windows grow with contributions."""
    t = GRAPH_TEXT[lang]
    days = contrib["days"]
    first = date.fromisoformat(days[0][0])
    offset = (first.weekday() + 1) % 7
    weekly = {}
    for i, (_, c) in enumerate(days):
        weekly[(offset + i) // 7] = weekly.get((offset + i) // 7, 0) + c
    totals = [weekly[w] for w in sorted(weekly)]
    peak = max(totals) or 1
    step, bw, depth = 20, 14, 6
    x0 = (1200 - len(totals) * step) // 2
    base = 318
    svg = Svg(1200, 430, f"{t['city']}. {t['busiest_week']}: {peak}")
    backdrop(svg)
    # A hazy far layer across the whole width, so quiet months still read as a city at night.
    far = ""
    for i in range(len(totals) * 2):
        fh = 22 + (i * 7919 % 97) / 97 * 70
        fx = x0 - 6 + i * step / 2
        far += f"M{num(fx)} {base}V{num(base - fh)}h{num(step / 2 - 1)}V{base}z"
    svg.add(el("path", d=far, fill="#ffffff", fill_opacity=0.045))
    svg.styles.append(
        "@keyframes rise{from{transform:scaleY(0)}}"
        ".bld{transform-box:fill-box;transform-origin:bottom;animation:rise .9s cubic-bezier(.2,.7,.2,1) both}"
        "@keyframes show{from{opacity:0}}.lights{animation:show .8s ease 1.3s both}"
        "@keyframes flicker{0%,100%{opacity:1}45%{opacity:.25}55%{opacity:.9}}"
        ".tw{animation:flicker 3.2s ease-in-out infinite}"
        "@keyframes drift{from{transform:translateX(-14px)}to{transform:translateX(14px)}}"
        ".rip{animation:drift 6s ease-in-out infinite alternate}"
        # Living city: some lit windows switch off for a while, some dark ones switch on.
        "@keyframes off{0%,36%{opacity:1}40%,68%{opacity:0}72%,100%{opacity:1}}"
        "@keyframes on{0%,42%{opacity:0}46%,80%{opacity:1}84%,100%{opacity:0}}"
        ".off0{animation:off 9s ease-in-out -1s infinite}.off1{animation:off 13s ease-in-out -6s infinite}.off2{animation:off 17s ease-in-out -11s infinite}"
        ".on0{animation:on 8s ease-in-out -3s infinite}.on1{animation:on 12s ease-in-out -7s infinite}.on2{animation:on 15s ease-in-out -2s infinite}"
        "@media (prefers-reduced-motion:reduce){.bld,.tw,.rip,.lights,.off0,.off1,.off2,.on0,.on1,.on2{animation:none}.on0,.on1,.on2{opacity:0}}"
    )
    svg.text(64, 76, t["city"], SERIF_IT, 24, C["ink"])
    svg.text(64, 104, t["city_note"], BODY, 15, C["muted"])
    svg.text(1136, 76, [(f"{t['busiest_week']}  ", C["muted"]), (str(peak), C["ink"])], BODY, 16, text_anchor="end")

    groups, mirror, roofs = {}, "", []
    for w, total in enumerate(totals):
        share = total / peak
        h = 5 if not total else 14 + (share ** 0.7) * 176
        x, y = x0 + w * step, base - h
        roofs.append((x + bw / 2 + 3, y - 4))
        body = (
            el("polygon", points=f"{x + bw},{num(y)} {x + bw + depth},{num(y - 4)} {x + bw + depth},{base - 4} {x + bw},{base}", fill="#15120f")
            + el("polygon", points=f"{x},{num(y)} {x + depth},{num(y - 4)} {x + bw + depth},{num(y - 4)} {x + bw},{num(y)}", fill="#5a4a3d")
            + el("rect", x=x, y=num(y), width=bw, height=num(h), fill="url(#facade)")
        )
        svg.add(el("g", body, class_="bld", style=f"animation-delay:{w * 22}ms"))
        mirror += el("rect", x=x, y=base, width=bw, height=num(h * 0.55), fill="#1d1916")
        if not total:
            continue
        pct = 30 + 62 * share
        rows = int((h - 10) // 7)
        for r in range(rows):
            for col, wx in enumerate((x + 3, x + 8)):
                rect = f"M{wx} {num(y + 6 + r * 7)}h3v3h-3z"
                mix = w * 7919 + r * 104729 + col * 1299709
                if window_lit(w, r, col, pct):
                    group = "tw" if (w * 31 + r * 7 + col) % 23 == 0 else f"off{mix % 3}" if mix % 4 == 0 else "lit"
                elif mix % 6 == 0:
                    group = f"on{mix % 3}"
                else:
                    continue
                groups.setdefault(group, []).append(rect)
    lit = groups.get("lit", [])
    svg.defs.append(
        el("linearGradient", el("stop", offset=0, stop_color="#3d342c") + el("stop", offset=1, stop_color="#221d19"), id="facade", x1=0, y1=0, x2=0, y2=1)
    )
    lights = el("path", d="".join(lit), fill="#f4b884", fill_opacity=0.85)
    for name in sorted(k for k in groups if k != "lit"):
        lights += el("path", d="".join(groups[name]), fill="#ffd2a6" if name == "tw" else "#f4b884", fill_opacity=0.9, class_=name)
    svg.add(el("g", lights, class_="lights"))
    # The water: a faded mirror image and a few slow ripples.
    svg.defs.append(
        el("linearGradient", el("stop", offset=0, stop_color="#fff", stop_opacity=0.5) + el("stop", offset=1, stop_color="#fff", stop_opacity=0), id="fadew", x1=0, y1=0, x2=0, y2=1)
    )
    svg.defs.append(el("mask", el("rect", x=0, y=base, width=1200, height=110, fill="url(#fadew)"), id="water"))
    svg.add(el("g", mirror + el("path", d="".join(lit), fill="#f4b884", fill_opacity=0.5, transform=f"translate(0 {2 * base}) scale(1 -1)"), mask="url(#water)"))
    svg.add(el("path", d=f"M64 {base}H1136", stroke=C["line_strong"]))
    ripples = "".join(
        el("path", d=f"M{120 + (i * 173) % 900} {base + 14 + i * 11}h{60 + (i * 37) % 80}", stroke="#ffffff", stroke_opacity=0.08, stroke_linecap="round")
        for i in range(7)
    )
    svg.add(el("g", ripples, class_="rip"))
    roof_cat(svg, roofs, totals)
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


def fetch_contributions():
    """Daily contribution counts for the last year. Counts only: no repository names, so private work stays private."""
    token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        query = '{user(login:"%s"){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}' % USER
        request = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query}).encode(),
            headers={"Authorization": f"Bearer {token}", "User-Agent": f"{USER}-profile-builder"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                calendar = json.load(response)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            days = [[d["date"], d["contributionCount"]] for w in calendar["weeks"] for d in w["contributionDays"]]
            return {"total": calendar["totalContributions"], "days": days}
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"Contributions unavailable ({error}), using {CONTRIB.relative_to(ROOT)}")
    return json.loads(CONTRIB.read_text())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    live = fetch_live()
    LIVE.write_text(json.dumps(live, ensure_ascii=False, indent=2) + "\n")
    contrib = fetch_contributions()
    CONTRIB.write_text(json.dumps(contrib, separators=(",", ":")) + "\n")
    outputs = {}
    for lang in LANGS:
        outputs[f"hero.{lang}.svg"] = hero(lang, live)
        outputs[f"graph.{lang}.svg"] = contribution_graph(lang, contrib)
        outputs[f"city.{lang}.svg"] = skyline(lang, contrib)
        for index, project in enumerate(PROJECTS, start=1):
            outputs[f"card-{project['slug']}.{lang}.svg"] = card(project, index, lang)
        outputs[f"footer.{lang}.svg"] = footer(lang)
    # Drop blocks that are no longer generated, so the folder always matches the README.
    for stale in OUT.glob("*.svg"):
        if stale.name not in outputs:
            stale.unlink()
    for name, svg in outputs.items():
        path = OUT / name
        path.write_text(svg.render())
        print(f"{name:32} {path.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
