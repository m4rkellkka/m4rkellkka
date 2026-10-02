from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PROFILE = ASSETS / "mikhail-savushkin-profile.jpg"
PDF_OUT = ASSETS / "mikhail-savushkin-resume.pdf"
SOCIAL_OUT = ASSETS / "mikhail-savushkin-social-preview.png"

FONT_REGULAR = ASSETS / "fonts" / "Manrope-Regular.ttf"
FONT_BOLD = ASSETS / "fonts" / "Manrope-Bold.ttf"
FONT_DISPLAY = ASSETS / "fonts" / "Unbounded-Bold.ttf"
FONT_MONO = ASSETS / "fonts" / "JetBrainsMono-Regular.ttf"

# Canonical source for generated deploy assets:
# - assets/mikhail-savushkin-resume.pdf
# - assets/mikhail-savushkin-social-preview.png


RESUME = {
    "name": "Mikhail Savushkin",
    "role": "Full-Stack Engineer | Next.js, React & AI",
    "location": "Istanbul, Turkiye",
    "email": "savushkinwork@gmail.com",
    "linkedin": "linkedin.com/in/mikhail-savushkin-993a33408",
    "summary": (
        "Full-stack engineer with a Data Science background. I build web products and connect them to AI: "
        "Next.js interfaces that work on a phone, Postgres with real access control, and LLM pipelines that "
        "take manual work off people. One year as a Data Scientist at Yandex anchors the data-first habit."
    ),
    "proof": [
        "1 year at Yandex - production data work, pipelines, analytical models, and cross-functional delivery.",
        "Next.js, React, Supabase - full-stack apps with phone-first interfaces and row-level security in Postgres.",
        "AI in real operations - LLM pipelines for sales QA and hiring, connected through webhooks and CRMs.",
    ],
    "systems": [
        {
            "title": "Tamam - requests and approvals for a clinic (in pilot)",
            "bullets": [
                "Next.js and Supabase app that replaces WhatsApp threads with one queue per role: sellers file requests "
                "from a phone, managers approve, the coordinator carries them out and exports to Excel.",
                "5 roles enforced by Postgres row-level security and covered by pgTAP tests; 4 UI languages including Arabic (RTL).",
                "Stack: Next.js, React, TypeScript, Supabase, Postgres RLS, Vercel.",
            ],
        },
        {
            "title": "CV screening assistant for HR (MVP demo)",
            "bullets": [
                "Reads PDF, DOCX and scanned CVs (OCR), strips personal data before the LLM, and rates every hiring "
                "criterion with a verbatim quote from the CV.",
                "The score and ranking are computed in code, not by the model; HR gets interview questions and an Excel export, and makes every decision.",
                "Stack: Next.js, TypeScript, Claude API, Ollama, Tesseract OCR.",
            ],
        },
        {
            "title": "AI reviewer for WhatsApp sales conversations",
            "bullets": [
                "Connected messaging data to an LLM-backed QA flow that reviews conversations and extracts sales signals.",
                "Turns unstructured chats into audit-ready feedback for managers and sales quality review.",
                "Stack: LLM APIs, webhooks, Node.js, QA logic.",
            ],
        },
    ],
    "experience": [
        {
            "role": "Full-Stack Engineer (Web & AI)",
            "org": "International Plus / Power International - Istanbul",
            "date": "May 2026 - Present",
            "bullets": [
                "Built Tamam, the clinic's request and approval app (Next.js, Supabase), now in pilot with the sales teams.",
                "Built a CV screening assistant that helps HR shortlist candidates for multilingual sales roles.",
                "Architected an AI-driven QA agent for WhatsApp sales: LLMs connected via webhooks to automate sales "
                "analysis and reduce manual auditing time.",
            ],
        },
        {
            "role": "Medical Advisor",
            "org": "International Plus - Istanbul",
            "date": "Dec 2025 - May 2026",
            "bullets": [
                "Managed CRM workflows and client interactions across live sales processes.",
                "Turned operational knowledge into sharper requirements for AI-driven QA bots and automation.",
            ],
        },
        {
            "role": "Data Scientist",
            "org": "Yandex - Moscow",
            "date": "Sep 2022 - Sep 2023",
            "bullets": [
                "Built and maintained data pipelines for cleaning large-scale datasets.",
                "Developed analytical models that surfaced insights for business decisions.",
                "Partnered cross-functionally to translate requirements into data solutions.",
            ],
        },
    ],
    "skills": [
        "TypeScript",
        "React",
        "Next.js",
        "Tailwind CSS",
        "Node.js",
        "PostgreSQL",
        "Supabase",
        "REST APIs",
        "Webhooks",
        "LLM APIs",
        "AI agents",
        "Local LLMs",
        "Python",
        "Pandas",
        "SQL",
        "Vercel",
        "AWS",
    ],
    "education": "Istanbul Topkapi University - B.Eng., Computer Engineering, Oct 2023 - Aug 2028 (in progress).",
}


def register_fonts():
    pdfmetrics.registerFont(TTFont("ResumeSans", str(FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont("ResumeSans-Bold", str(FONT_BOLD)))
    pdfmetrics.registerFont(TTFont("ResumeDisplay", str(FONT_DISPLAY)))
    pdfmetrics.registerFont(TTFont("ResumeMono", str(FONT_MONO)))


def draw_background(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#0b0b0d"))
    canvas.rect(0, 0, A4[0], A4[1], fill=True, stroke=False)
    canvas.restoreState()


def style_sheet():
    base = getSampleStyleSheet()
    ink = colors.HexColor("#e0e0e0")
    muted = colors.HexColor("#a0a0a0")
    accent = colors.HexColor("#f0642f")

    return {
        "name": ParagraphStyle(
            "Name",
            parent=base["Normal"],
            fontName="ResumeDisplay",
            fontSize=28,
            leading=32,
            textColor=ink,
            spaceAfter=3,
        ),
        "role": ParagraphStyle(
            "Role",
            parent=base["Normal"],
            fontName="ResumeSans-Bold",
            fontSize=11,
            leading=15,
            textColor=accent,
            spaceAfter=8,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="ResumeMono",
            fontSize=8.8,
            leading=12,
            textColor=muted,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Normal"],
            fontName="ResumeDisplay",
            fontSize=12,
            leading=16,
            textColor=ink,
            spaceBefore=9,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="ResumeSans",
            fontSize=9.3,
            leading=13.5,
            textColor=ink,
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "muted": ParagraphStyle(
            "Muted",
            parent=base["Normal"],
            fontName="ResumeSans",
            fontSize=8.7,
            leading=12,
            textColor=muted,
            spaceAfter=4,
        ),
        "item_title": ParagraphStyle(
            "ItemTitle",
            parent=base["Normal"],
            fontName="ResumeSans-Bold",
            fontSize=9.8,
            leading=13,
            textColor=ink,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="ResumeSans",
            fontSize=8.8,
            leading=12,
            textColor=ink,
            leftIndent=8,
            firstLineIndent=-8,
            spaceAfter=1,
        ),
    }


def bullet_items(items, styles):
    return [Paragraph(f"- {item}", styles["bullet"]) for item in items]


def build_pdf():
    register_fonts()
    styles = style_sheet()
    doc = SimpleDocTemplate(
        str(PDF_OUT),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Mikhail Savushkin Resume",
        author="Mikhail Savushkin",
    )

    story = [
        Paragraph(RESUME["name"], styles["name"]),
        Paragraph(RESUME["role"], styles["role"]),
        Paragraph(
            f"{RESUME['location']} | {RESUME['email']} | {RESUME['linkedin']}",
            styles["meta"],
        ),
        Paragraph(RESUME["summary"], styles["body"]),
        Paragraph("Proof", styles["section"]),
        *bullet_items(RESUME["proof"], styles),
        Paragraph("Selected Systems", styles["section"]),
    ]

    for system in RESUME["systems"]:
        story.append(
            KeepTogether(
                [
                    Paragraph(system["title"], styles["item_title"]),
                    *bullet_items(system["bullets"], styles),
                    Spacer(1, 2),
                ]
            )
        )

    story.append(Paragraph("Experience", styles["section"]))
    for item in RESUME["experience"]:
        story.append(
            KeepTogether(
                [
                    Paragraph(item["role"], styles["item_title"]),
                    Paragraph(f"{item['org']} | {item['date']}", styles["muted"]),
                    *bullet_items(item["bullets"], styles),
                    Spacer(1, 2),
                ]
            )
        )

    story.extend(
        [
            Paragraph("Core Stack", styles["section"]),
            Paragraph(", ".join(RESUME["skills"]), styles["body"]),
            Paragraph("Education", styles["section"]),
            Paragraph(RESUME["education"], styles["body"]),
        ]
    )

    doc.build(story, onFirstPage=draw_background, onLaterPages=draw_background)


def draw_wrapped(draw, xy, text, font, fill, width, line_gap=8):
    x, y = xy
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            probe = f"{current} {word}".strip()
            if draw.textbbox((0, 0), probe, font=font)[2] <= width:
                current = probe
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def build_social_preview():
    width, height = 1200, 630
    bg = Image.new("RGB", (width, height), "#0b0b0d")
    draw = ImageDraw.Draw(bg)

    # Clean dark design with orange accent
    portrait = Image.open(PROFILE).convert("RGB")
    portrait = portrait.resize((360, 480))
    # Soften harsh contrasts instead of amplifying
    portrait = ImageEnhance.Color(portrait).enhance(0.9)
    portrait = ImageEnhance.Brightness(portrait).enhance(0.95)
    
    mask = Image.new("L", portrait.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, portrait.width, portrait.height), radius=20, fill=255)
    bg.paste(portrait, (760, 75), mask)
    
    # Subtle frame around portrait
    draw.rounded_rectangle((760, 75, 1120, 555), radius=20, outline="#2a2a2d", width=2)

    # Accent badge
    draw.rectangle((760, 465, 1120, 555), fill="#121214")
    draw.text((790, 498), "Location", font=ImageFont.truetype(str(FONT_MONO), 18), fill="#f0642f")
    draw.text((890, 494), "Istanbul, Turkiye", font=ImageFont.truetype(str(FONT_BOLD), 22), fill="#e0e0e0")

    title_font = ImageFont.truetype(str(FONT_DISPLAY), 72)
    role_font = ImageFont.truetype(str(FONT_BOLD), 32)
    body_font = ImageFont.truetype(str(FONT_REGULAR), 26)
    chip_font = ImageFont.truetype(str(FONT_MONO), 18)

    # Status chip, sized to its label
    status = "Open to full-stack / AI roles"
    chip_right = 125 + draw.textlength(status, font=chip_font) + 26
    draw.rounded_rectangle((70, 98, chip_right, 146), radius=24, outline="#2a2a2d", fill="#161616")
    draw.ellipse((94, 116, 106, 128), fill="#f0642f")
    draw.text((125, 112), status, font=chip_font, fill="#a0a0a0")

    # Typography
    draw.text((70, 195), "Mikhail", font=title_font, fill="#e0e0e0")
    draw.text((70, 275), "Savushkin", font=title_font, fill="#e0e0e0")
    
    role_bottom = draw_wrapped(
        draw,
        (72, 385),
        "Full-Stack Engineer | Next.js, React & AI",
        role_font,
        "#f0642f",
        640,
        line_gap=10,
    )
    draw_wrapped(
        draw,
        (72, role_bottom + 25),
        "Web products and AI integrations that remove manual work, grounded in a data science background at Yandex.",
        body_font,
        "#a0a0a0",
        650,
        line_gap=12,
    )

    bg.save(SOCIAL_OUT, "PNG", optimize=True)


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    build_pdf()
    build_social_preview()
    print(f"generated {PDF_OUT.relative_to(ROOT)}")
    print(f"generated {SOCIAL_OUT.relative_to(ROOT)}")
