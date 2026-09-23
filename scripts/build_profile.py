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
        "location": "ISTANBUL, TÜRKIYE",
        "name": "Mikhail Savushkin",
        "role": "AI SOLUTIONS INTEGRATOR",
        "role_tail": " / BACKEND & AUTOMATION",
        "tagline": "I don't just write code — I build data-driven systems that kill real bottlenecks.",
        "status": "latest push",
        "pipeline_label": "// WHAT I BUILD",
        "pipeline": [
            ("chat", "WhatsApp · CRM"),
            ("webhook", "Node.js · AWS"),
            ("LLM", "LLM APIs · agents"),
            ("insight", "QA report · signals"),
        ],
        "stack_label": "// STACK",
        "stack": [
            ("DATA", ["Python", "Pandas", "SQL", "Seaborn", "Jupyter"]),
            ("BACKEND", ["Node.js", "TypeScript", "REST APIs", "Webhooks", "AWS"]),
            ("AI", ["LLM APIs", "AI agents", "Local LLMs", "ML tooling"]),
        ],
        "also": "also: Java · C++ · Verilog · Tauri · Next.js · Tkinter",
        "pushed": "pushed",
        "private": "private",
        "about_label": "// ABOUT",
        "about": "I build backend systems that connect AI to real operations: LLM integrations, webhooks and automation that take manual work off people. The data-first habit comes from a year as a Data Scientist at Yandex.",
        "timeline": [
            ("SEP 2022", "Yandex", "Data Scientist · Moscow"),
            ("OCT 2023", "Topkapı University", "B.Eng. Computer Engineering"),
            ("DEC 2025", "International Plus", "Medical Advisor · CRM"),
            ("MAY 2026", "International Plus", "Backend Engineer · AI"),
        ],
        "now": "NOW",
        "contact_label": "// CONTACT",
        "contact_title": "Let's build something that removes work, not adds it.",
        "contact_note": "this profile rebuilds itself every morning · profile.yml → build_profile.py",
        "buttons": {"resume": "Resume", "linkedin": "LinkedIn", "email": "Email"},
    },
    "ru": {
        "location": "СТАМБУЛ, ТУРЦИЯ",
        "name": "Михаил Савушкин",
        "role": "ИНТЕГРАТОР AI-РЕШЕНИЙ",
        "role_tail": " / BACKEND & AUTOMATION",
        "tagline": "Я не просто пишу код — я строю data-driven системы, которые убирают реальные узкие места.",
        "status": "последний пуш",
        "pipeline_label": "// ЧТО Я СТРОЮ",
        "pipeline": [
            ("чат", "WhatsApp · CRM"),
            ("webhook", "Node.js · AWS"),
            ("LLM", "LLM API · агенты"),
            ("инсайт", "QA-отчёт · сигналы"),
        ],
        "stack_label": "// СТЕК",
        "stack": [
            ("ДАННЫЕ", ["Python", "Pandas", "SQL", "Seaborn", "Jupyter"]),
            ("BACKEND", ["Node.js", "TypeScript", "REST API", "Webhooks", "AWS"]),
            ("AI", ["LLM API", "AI-агенты", "Локальные LLM", "ML-инструменты"]),
        ],
        "also": "ещё: Java · C++ · Verilog · Tauri · Next.js · Tkinter",
        "pushed": "пуш",
        "private": "private",
        "about_label": "// ОБО МНЕ",
        "about": "Строю backend-системы, которые подключают AI к реальным процессам: LLM-интеграции, webhooks и автоматизацию, которая снимает с людей ручную работу. Data-first подход — из года работы Data Scientist в Yandex.",
        "timeline": [
            ("СЕН 2022", "Yandex", "Data Scientist · Москва"),
            ("ОКТ 2023", "Topkapı University", "Компьютерная инженерия"),
            ("ДЕК 2025", "International Plus", "Medical Advisor · CRM"),
            ("МАЙ 2026", "International Plus", "Backend Engineer · AI"),
        ],
        "now": "СЕЙЧАС",
        "contact_label": "// КОНТАКТЫ",
        "contact_title": "Давайте строить системы, которые убирают работу, а не добавляют её.",
        "contact_note": "профиль пересобирается сам каждое утро · profile.yml → build_profile.py",
        "buttons": {"resume": "Резюме", "linkedin": "LinkedIn", "email": "Email"},
    },
}

# Card order is the README order: two per row.
PROJECTS = [
    {
        "slug": "lumis",
        "repo": "Lumis",
        "title": "Lumis",
        "label": {"en": "LOCAL-FIRST AI", "ru": "LOCAL-FIRST AI"},
        "desc": {
            "en": "Exam prep app: topic analysis, AI-generated flashcards and quizzes, spaced repetition and mock exams — all on local LLMs.",
            "ru": "Подготовка к экзаменам: анализ тем, AI-карточки и квизы, интервальные повторения и пробные экзамены — на локальных LLM.",
        },
        "tags": ["Tauri", "Next.js", "TypeScript", "Local LLMs"],
    },
    {
        "slug": "whatsapp-qa",
        "repo": None,
        "title": "WhatsApp QA Agent",
        "label": {"en": "IN PRODUCTION", "ru": "В ПРОДАКШЕНЕ"},
        "desc": {
            "en": "LLM reviewer for sales chats: webhooks pull conversations, the model extracts sales signals and returns audit-ready feedback.",
            "ru": "LLM-ревьюер продажных чатов: webhooks забирают переписки, модель находит сигналы продаж и готовит фидбек для аудита.",
        },
        "tags": ["LLM APIs", "Webhooks", "Node.js", "QA logic"],
        "org": "International Plus",
    },
    {
        "slug": "snake-ai",
        "repo": "SnakeAI_Project",
        "title": "SnakeAI",
        "label": {"en": "IMITATION LEARNING", "ru": "IMITATION LEARNING"},
        "desc": {
            "en": "A CNN agent learns Snake by imitating a Hamiltonian-cycle teacher (behavioral cloning + DAgger-lite), with a Tkinter lab.",
            "ru": "CNN-агент учится «Змейке», подражая учителю на гамильтоновом цикле (behavioral cloning + DAgger-lite). Tkinter-дашборд.",
        },
        "tags": ["Python", "CNN", "DAgger", "Tkinter"],
    },
    {
        "slug": "clinic",
        "repo": "clinic-retention-analysis",
        "title": "Clinic Retention",
        "label": {"en": "DATA ANALYSIS", "ru": "АНАЛИЗ ДАННЫХ"},
        "desc": {
            "en": "EDA of patient no-shows to decide where a clinic should spend its scheduling effort and marketing budget.",
            "ru": "EDA неявок пациентов: куда клинике направить усилия по расписанию и маркетинговый бюджет.",
        },
        "tags": ["Python", "Pandas", "Seaborn", "Jupyter"],
    },
]

LANGUAGE_COLORS = {
    "TypeScript": "#3178c6",
    "Python": "#3572a5",
    "Jupyter Notebook": "#da5b0b",
    "Java": "#b07219",
    "Verilog": "#b2b7f8",
}


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


# Same tokens as the :root block in index.html, so the profile and the resume site share one palette.
C = {
    "bg": oklch(0.085, 0, 0),
    "raised": oklch(0.115, 0.003, 70),
    "surface": oklch(0.155, 0.006, 70),
    "surface_strong": oklch(0.205, 0.008, 70),
    "ink": oklch(0.925, 0.014, 78),
    "ink_strong": oklch(0.985, 0.005, 78),
    "muted": oklch(0.705, 0.018, 72),
    "muted_soft": oklch(0.575, 0.014, 72),
    "primary": oklch(0.645, 0.185, 39),
    "amber": oklch(0.755, 0.145, 72),
    "teal": oklch(0.76, 0.105, 190),
}
LINE = "rgba(255,255,255,0.08)"
LINE_STRONG = "rgba(255,255,255,0.16)"


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
        Face("pf-display", "Unbounded-Bold.ttf"),
        Face("pf-body", "Manrope-Regular.ttf"),
        Face("pf-mono", "JetBrainsMono-Regular.ttf"),
        Face("pf-mono-md", "JetBrainsMono-Medium.ttf"),
    )
}
DISPLAY, BODY, MONO, MONO_MD = (FACES[k] for k in ("pf-display", "pf-body", "pf-mono", "pf-mono-md"))


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
        """content is a string or a list of (text, fill) spans."""
        spans = [(content, None)] if isinstance(content, str) else content
        inner = ""
        for part, span_fill in spans:
            self.chars.setdefault(face.family, set()).update(part)
            inner += el("tspan", escape(part), fill=span_fill) if span_fill else escape(part)
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


def backdrop(svg, radius, glow=None, noise=True):
    """Resume-site background: dark gradient, fading 48px grid, grain, optional orange glow."""
    w, h = svg.width, svg.height
    svg.defs += [
        el(
            "linearGradient",
            el("stop", offset=0, stop_color=C["raised"]) + el("stop", offset=1, stop_color=C["bg"]),
            id="bg", x1=0, y1=0, x2=0, y2=1,
        ),
        el(
            "pattern",
            el("path", d="M48 0H0V48", fill="none", stroke="#fff", stroke_opacity=0.045),
            id="grid", width=48, height=48, patternUnits="userSpaceOnUse",
        ),
        el(
            "linearGradient",
            el("stop", offset=0, stop_color="#fff") + el("stop", offset=0.85, stop_color="#fff", stop_opacity=0),
            id="fade", x1=0, y1=0, x2=0, y2=1,
        ),
        el("mask", el("rect", width=w, height=h, fill="url(#fade)"), id="grid-mask"),
        el("clipPath", el("rect", width=w, height=h, rx=radius), id="frame"),
    ]
    layers = [el("rect", width=w, height=h, fill="url(#bg)")]
    if glow:
        cx, cy, r = glow
        svg.defs.append(
            el(
                "radialGradient",
                el("stop", offset=0, stop_color=C["primary"], stop_opacity=0.2)
                + el("stop", offset=1, stop_color=C["primary"], stop_opacity=0),
                id="glow", cx=cx, cy=cy, r=r,
            )
        )
        layers.append(el("rect", width=w, height=h, fill="url(#glow)"))
    layers.append(el("rect", width=w, height=h, fill="url(#grid)", mask="url(#grid-mask)"))
    if noise:
        # Only on static images: an animated SVG would recompute the turbulence every frame.
        svg.defs.append(
            el(
                "filter",
                el("feTurbulence", type="fractalNoise", baseFrequency=0.9, numOctaves=3, stitchTiles="stitch")
                + el("feColorMatrix", type="saturate", values=0),
                id="grain",
            )
        )
        layers.append(el("rect", width=w, height=h, filter="url(#grain)", opacity=0.07))
    svg.add(el("g", "".join(layers), clip_path="url(#frame)"))
    svg.add(el("rect", x=0.5, y=0.5, width=w - 1, height=h - 1, rx=radius - 0.5, fill="none", stroke=LINE_STRONG))


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


def section_label(svg, x, y, label, right):
    svg.text(x, y, label, MONO, 14, C["muted_soft"], letter_spacing=2)
    start = x + MONO.width(label, 14, 2) + 14
    svg.add(el("path", d=f"M{num(start)} {y - 5}H{right}", stroke=LINE_STRONG))


def chip(svg, x, y, label, size, height):
    width = MONO.width(label, size) + 24
    svg.add(el("rect", x=num(x), y=y, width=num(width), height=height, rx=8, fill=C["surface"], stroke=LINE))
    svg.text(num(x + 12), num(y + height / 2 + size * 0.36), label, MONO, size, C["ink"])
    return width


def star(cx, cy, r):
    points = []
    for i in range(10):
        radius = r if i % 2 == 0 else r * 0.45
        angle = math.radians(-90 + i * 36)
        points.append(f"{num(cx + radius * math.cos(angle))},{num(cy + radius * math.sin(angle))}")
    return " ".join(points)


def hero(lang, live):
    t = CONTENT[lang]
    svg = Svg(1200, 460, f"{t['name']} — {t['role']}")
    pad, right = 64, 1136
    backdrop(svg, 18, glow=(0.88, 0.02, 0.62), noise=False)
    svg.styles.append(
        "@keyframes ping{0%{transform:scale(1);opacity:.7}80%,100%{transform:scale(2.6);opacity:0}}"
        ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.2s cubic-bezier(0,0,.2,1) infinite}"
        "@media (prefers-reduced-motion:reduce){.ping{animation:none;opacity:0}.packet{display:none}}"
    )

    # Top row: location on the left, live status pill on the right.
    svg.text(pad, 76, t["location"], MONO, 15, C["muted_soft"], letter_spacing=2.5)
    latest = live["latest"]
    title = next((p["title"] for p in PROJECTS if p["repo"] == latest["name"]), latest["name"])
    status = [(f"{t['status']} → ", C["muted"]), (title, C["ink_strong"]), (f" · {day_first(latest['pushed'])}", C["muted"])]
    status_width = sum(MONO.width(part, 15) for part, _ in status)
    pill_x = right - status_width - 52
    svg.add(
        el("rect", x=num(pill_x), y=50, width=num(status_width + 52), height=38, rx=19, fill=C["surface"], stroke=LINE_STRONG),
        el("circle", cx=num(pill_x + 22), cy=69, r=5, fill=C["teal"], class_="ping"),
        el("circle", cx=num(pill_x + 22), cy=69, r=5, fill=C["teal"]),
    )
    svg.text(num(pill_x + 36), 74, status, MONO, 15)

    # Name, role, tagline.
    svg.text(pad, 160, t["name"], DISPLAY, num(fit(DISPLAY, t["name"], 62, right - pad)), C["ink_strong"])
    svg.text(pad, 206, [(t["role"], C["primary"]), (t["role_tail"], C["muted_soft"])], MONO_MD, 19, letter_spacing=1.5)
    for i, line in enumerate(wrap(BODY, t["tagline"], 23, right - pad, 2)):
        svg.text(pad, 252 + i * 32, line, BODY, 23, C["ink"])

    # Pipeline: packets run left to right behind the nodes and turn teal once they leave the LLM.
    section_label(svg, pad, 318, t["pipeline_label"], right)
    node_w, node_h, node_y = 196, 52, 344
    gap = (right - pad - 4 * node_w) / 3
    xs = [pad + i * (node_w + gap) for i in range(4)]
    mid = node_y + node_h / 2
    start, end = xs[0] + node_w / 2, xs[3] + node_w / 2
    for a, b in zip(xs, xs[1:]):
        x1, x2 = a + node_w + 10, b - 12
        svg.add(
            el("path", d=f"M{num(x1)} {num(mid)}H{num(x2)}", stroke=C["muted_soft"], stroke_opacity=0.55, stroke_dasharray="3 6"),
            el("path", d=f"M{num(x2 - 7)} {num(mid - 6)}L{num(x2)} {num(mid)}L{num(x2 - 7)} {num(mid + 6)}", fill="none", stroke=C["muted_soft"], stroke_width=1.5),
        )
    switch = (xs[2] + node_w / 2 - start) / (end - start)
    # 4 packets over 3 gaps: their spacing never lines up with the nodes, so some are always visible.
    duration, packets = 6.0, 4
    for i in range(packets):
        timing = {"dur": f"{num(duration)}s", "begin": f"-{num(i * duration / packets)}s", "repeatCount": "indefinite"}
        paint = el("animate", attributeName="fill", values=f"{C['primary']};{C['teal']}", keyTimes=f"0;{num(switch)}", calcMode="discrete", **timing)
        motion = el("animateMotion", path=f"M{num(start)} {num(mid)}H{num(end)}", **timing)
        svg.add(el("circle", paint + motion, r=5.5, fill=C["primary"], class_="packet"))
    for i, (x, (label, caption)) in enumerate(zip(xs, t["pipeline"])):
        accent = {2: C["primary"], 3: C["teal"]}.get(i)
        svg.add(el("rect", x=num(x), y=node_y, width=node_w, height=node_h, rx=12, fill=C["surface"], stroke=accent or LINE_STRONG, stroke_opacity=0.7 if accent else None))
        if i == 2:
            svg.add(el("rect", x=num(x), y=node_y, width=node_w, height=node_h, rx=12, fill=C["primary"], opacity=0.1))
        svg.text(num(x + node_w / 2), num(mid + 6.5), label, MONO_MD, 18, C["ink_strong"], text_anchor="middle")
        svg.text(num(x + node_w / 2), 424, caption, MONO, 13.5, C["muted_soft"], text_anchor="middle")
    return svg


def stack(lang):
    t = CONTENT[lang]
    pad, right, gap = 64, 1136, 44
    col_w = (right - pad - 2 * gap) / 3
    layout, rows_bottom = [], 0
    for col, (name, chips) in enumerate(t["stack"]):
        x0 = pad + col * (col_w + gap)
        x, y, placed = x0, 150, []
        for label in chips:
            width = MONO.width(label, 15) + 24
            if x + width > x0 + col_w and x > x0:
                x, y = x0, y + 44
            placed.append((x, y, label))
            x += width + 8
        layout.append((x0, name, placed))
        rows_bottom = max(rows_bottom, y + 34)

    svg = Svg(1200, rows_bottom + 78, f"Stack — {t['also']}")
    backdrop(svg, 18)
    section_label(svg, pad, 56, t["stack_label"], right)
    for col, (x0, name, placed) in enumerate(layout):
        line_end = x0 + col_w
        svg.text(num(x0), 106, f"0{col + 1}", MONO_MD, 15, C["primary"])
        svg.text(num(x0 + 34), 107, name, DISPLAY, 21, C["ink_strong"])
        svg.add(el("path", d=f"M{num(x0)} 126H{num(line_end)}", stroke=LINE_STRONG))
        if col < 2:
            tip = line_end + gap / 2 + 6
            svg.add(el("path", d=f"M{num(tip - 12)} 120L{num(tip - 6)} 126L{num(tip - 12)} 132", fill="none", stroke=C["primary"], stroke_width=1.5))
        for x, y, label in placed:
            chip(svg, x, y, label, 15, 34)
    svg.text(pad, rows_bottom + 44, t["also"], MONO, 14, C["muted_soft"])
    return svg


def card(project, index, lang, live):
    t = CONTENT[lang]
    w, h, pad = 600, 320, 36
    svg = Svg(w, h, f"{project['title']} — {project['desc'][lang]}")
    backdrop(svg, 16, glow=(1.0, 0.0, 0.7))

    svg.text(pad, 54, [(f"0{index}", C["primary"]), (f"  /  {project['label'][lang]}", C["muted_soft"])], MONO_MD, 14, letter_spacing=1.5)
    ax, ay = w - pad - 14, 40
    svg.add(el("path", d=f"M{ax} {ay + 14}L{ax + 14} {ay}M{ax + 4} {ay}H{ax + 14}V{ay + 10}", fill="none", stroke=C["muted"], stroke_width=2, stroke_linecap="round", stroke_linejoin="round"))

    svg.text(pad, 104, project["title"], DISPLAY, num(fit(DISPLAY, project["title"], 30, w - 2 * pad)), C["ink_strong"])
    for i, line in enumerate(wrap(BODY, project["desc"][lang], 19, w - 2 * pad, 3)):
        svg.text(pad, 144 + i * 28, line, BODY, 19, C["muted"])

    x = pad
    for tag in project["tags"]:
        if x + MONO.width(tag, 13.5) + 24 > w - pad:
            break
        x += chip(svg, x, 222, tag, 13.5, 30) + 8

    svg.add(el("path", d=f"M{pad} 270H{w - pad}", stroke=LINE))
    base = 300
    if project["repo"]:
        repo = live["repos"][project["repo"]]
        language = repo["language"] or "—"
        svg.add(el("circle", cx=pad + 6, cy=base - 5, r=6, fill=LANGUAGE_COLORS.get(language, C["muted"])))
        svg.text(pad + 20, base, language, MONO, 14, C["muted"])
        if repo["stars"]:
            sx = pad + 20 + MONO.width(language, 14) + 24
            svg.add(el("polygon", points=star(sx + 7, base - 5, 8), fill=C["amber"]))
            svg.text(num(sx + 20), base, str(repo["stars"]), MONO, 14, C["muted"])
        svg.text(w - pad, base, f"{t['pushed']} {day_first(repo['pushed'])}", MONO, 14, C["muted_soft"], text_anchor="end")
    else:
        svg.add(el("circle", cx=pad + 6, cy=base - 5, r=6, fill=C["teal"]))
        svg.text(pad + 20, base, t["private"], MONO, 14, C["muted"])
        svg.text(w - pad, base, project["org"], MONO, 14, C["muted_soft"], text_anchor="end")
    return svg


def about(lang):
    t = CONTENT[lang]
    pad, right = 64, 1136
    lines = wrap(BODY, t["about"], 22, right - pad, 3)
    line_y = 104 + (len(lines) - 1) * 32 + 80
    svg = Svg(1200, line_y + 104, t["about"])
    backdrop(svg, 18)
    section_label(svg, pad, 56, t["about_label"], right)
    for i, line in enumerate(lines):
        svg.text(pad, 104 + i * 32, line, BODY, 22, C["ink"])

    # Career drawn like the hero pipeline: orange behind, teal for where I am now.
    stops = t["timeline"]
    col_w = (right - pad) / len(stops)
    xs = [pad + 6 + i * col_w for i in range(len(stops))]
    svg.defs.append(
        el(
            "linearGradient",
            el("stop", offset=0, stop_color=C["primary"]) + el("stop", offset=1, stop_color=C["teal"]),
            id="path", gradientUnits="userSpaceOnUse", x1=num(xs[0]), y1=0, x2=num(xs[-1]), y2=0,
        )
    )
    svg.add(
        el("path", d=f"M{num(xs[0])} {line_y}H{num(xs[-1])}", stroke="url(#path)", stroke_width=2),
        el("path", d=f"M{num(xs[-1])} {line_y}H{right}", stroke=C["teal"], stroke_opacity=0.5, stroke_dasharray="3 6"),
    )
    for i, (x, (date, org, role)) in enumerate(zip(xs, stops)):
        current = i == len(stops) - 1
        color = C["teal"] if current else C["primary"]
        svg.text(num(x - 6), line_y - 22, date, MONO_MD, 14, color, letter_spacing=1.5)
        if current:
            pill_x = x - 6 + MONO_MD.width(date, 14, 1.5) + 10
            pill_w = MONO_MD.width(t["now"], 11.5, 1.5) + 18
            svg.add(
                el("rect", x=num(pill_x), y=line_y - 40, width=num(pill_w), height=24, rx=12, fill=C["teal"], fill_opacity=0.14, stroke=C["teal"], stroke_opacity=0.5),
                el("circle", cx=num(x), cy=line_y, r=13, fill=C["teal"], opacity=0.16),
            )
            svg.text(num(pill_x + 9), line_y - 24, t["now"], MONO_MD, 11.5, C["teal"], letter_spacing=1.5)
        svg.add(el("circle", cx=num(x), cy=line_y, r=6, fill=C["teal"] if current else C["bg"], stroke=color, stroke_width=2))
        svg.text(num(x - 6), line_y + 40, org, DISPLAY, num(fit(DISPLAY, org, 17, col_w - 28)), C["ink_strong"])
        svg.text(num(x - 6), line_y + 66, role, MONO, 13.5, C["muted_soft"])
    return svg


def contact(lang):
    t = CONTENT[lang]
    pad, right = 64, 1136
    lines = wrap(DISPLAY, t["contact_title"], 28, right - pad, 2)
    note_y = 110 + (len(lines) - 1) * 42 + 50
    svg = Svg(1200, note_y + 44, t["contact_title"])
    backdrop(svg, 18, glow=(0.1, 1.0, 0.75))
    section_label(svg, pad, 56, t["contact_label"], right)
    for i, line in enumerate(lines):
        svg.text(pad, 110 + i * 42, line, DISPLAY, 28, C["ink_strong"])
    svg.text(pad, note_y, t["contact_note"], MONO, 14, C["muted_soft"])
    return svg


def button(label, primary):
    """One linkable pill: README images can carry only one link each, so every button is its own SVG."""
    size, h = 17, 56
    text_w = MONO_MD.width(label, size)
    w = 24 + text_w + 14 + 12 + 24
    ink = C["bg"] if primary else C["ink_strong"]
    svg = Svg(num(w), h, label)
    svg.add(el("rect", x=0.5, y=0.5, width=num(w - 1), height=h - 1, rx=12, fill=C["primary"] if primary else C["surface"], stroke=None if primary else LINE_STRONG))
    svg.text(24, num(h / 2 + size * 0.36), label, MONO_MD, size, ink)
    ax, ay = 24 + text_w + 14, h / 2 - 6
    svg.add(el("path", d=f"M{num(ax)} {num(ay + 12)}L{num(ax + 12)} {num(ay)}M{num(ax + 3)} {num(ay)}H{num(ax + 12)}V{num(ay + 9)}", fill="none", stroke=ink, stroke_width=2, stroke_linecap="round", stroke_linejoin="round"))
    return svg


def fetch_live():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{USER}-profile-builder"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    request = urllib.request.Request(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            repos = json.load(response)
    except (OSError, ValueError) as error:
        print(f"GitHub API unavailable ({error}), using {LIVE.relative_to(ROOT)}")
        return json.loads(LIVE.read_text())

    # The profile repo itself is left out: every bot commit would change its push date and trigger another commit.
    repos = [r for r in repos if not r["fork"] and r["name"] != USER]
    latest = max(repos, key=lambda r: r["pushed_at"])
    return {
        "latest": {"name": latest["name"], "pushed": latest["pushed_at"][:10]},
        "repos": {
            r["name"]: {"language": r["language"], "stars": r["stargazers_count"], "pushed": r["pushed_at"][:10]}
            for r in sorted(repos, key=lambda r: r["name"].lower())
        },
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    live = fetch_live()
    LIVE.write_text(json.dumps(live, ensure_ascii=False, indent=2) + "\n")
    outputs = {}
    for lang in LANGS:
        outputs[f"hero.{lang}.svg"] = hero(lang, live)
        outputs[f"about.{lang}.svg"] = about(lang)
        outputs[f"stack.{lang}.svg"] = stack(lang)
        for index, project in enumerate(PROJECTS, start=1):
            outputs[f"card-{project['slug']}.{lang}.svg"] = card(project, index, lang, live)
        outputs[f"contact.{lang}.svg"] = contact(lang)
        for key, label in CONTENT[lang]["buttons"].items():
            outputs[f"button-{key}.{lang}.svg"] = button(label, primary=key == "resume")
    for name, svg in outputs.items():
        path = OUT / name
        path.write_text(svg.render())
        print(f"{name:28} {path.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
