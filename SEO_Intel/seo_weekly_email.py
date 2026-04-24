"""
Listn SEO Intelligence — Weekly Email Report
Reads latest seo_raw JSON + seo_analysis MD, generates a 4-section PDF via Claude,
emails PDF to recipient. Run once a week after seo_monitor.py and seo_analyze.py.
"""

import glob
import html
import json
import re
import smtplib
import sys
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from pathlib import Path

import anthropic
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

BASE      = Path(__file__).parent          # SEO_Intel/
RECIPIENT = "digvijayudawat064@gmail.com"
MODEL     = "claude-sonnet-4-6"

# ── Keyword filter (same logic as seo_dashboard.py) ───────────────────────────
_BLOCKLIST = [
    "boyfriend", "girlfriend", "mother's day date", "mothers day date",
    "when is", "scan iphone", "scan on iphone", "romantic", "dating",
    "mom day", "mother day", "mothers day", "mother's day",
]
_ALLOWLIST_WORDS = [
    "memory", "memories", "story", "stories", "grandparent", "grandparents",
    "parent", "parents", "family", "memoir", "voice", "record", "preserve",
    "legacy", "gift", "gifts", "dad", "father", "mom", "mother", "elder",
    "aging", "remember", "heirloom", "keepsake", "capture", "biography",
    "life", "oral", "history", "ancestor", "generation",
]
_ALLOW_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _ALLOWLIST_WORDS) + r")\b",
    re.IGNORECASE,
)

def is_relevant(keyword: str) -> bool:
    kw = keyword.lower()
    if any(phrase in kw for phrase in _BLOCKLIST):
        return False
    return bool(_ALLOW_RE.search(kw))

def edge_for(keyword: str) -> str:
    kw = keyword.lower()
    if any(w in kw for w in ("grandparent", "grandparents", "grandma", "grandpa")):
        return "Meminto ranks 50s-90s with generic content. KD 0 — one post wins page one."
    if any(w in kw for w in ("dad", "father", "fathers")):
        return "StoryWorth ranks 88-102 despite being the obvious brand. Easily beatable."
    if any(w in kw for w in ("memory", "memories", "memoir", "story", "stories")):
        return "No competitor targets the voice-memory angle. Uncontested positioning."
    if any(w in kw for w in ("gift", "gifts", "present", "presents")):
        return "Gift-intent buyer. Add waitlist CTA for pre-launch conversion."
    return "Low KD, weak competitor presence. Voice angle differentiates."

# ── Hardcoded content roadmap ──────────────────────────────────────────────────
BLOG_POSTS = [
    {
        "title": "The Gift That Won't Get Donated: Why Voice Memories Beat Any Physical Present for Grandparents",
        "keywords": "grandparent gift ideas (14,800/mo, KD 0) · grandparents gift idea (14,800/mo, KD 0) · christmas gifts for grandparents (6,600/mo, KD 0)",
        "why": "Meminto ranks 50s-90s with a generic list. KD is zero. One well-optimized post lands page one. Add a waitlist CTA for direct pre-launch conversion.",
    },
    {
        "title": "How to Record Your Parent's Life Stories Before It's Too Late (A Guide for Adult Children)",
        "keywords": "parent memory book (880/mo, KD 8) · memory keeper (880/mo, KD 2) · memories books (8,100/mo, KD 0)",
        "why": "No competitor targets the adult-child urgency persona. Lead with loss aversion, then frame Listn as the frictionless option for older adults.",
    },
    {
        "title": "The Best Christmas Present for Dad That Isn't Another Gadget He'll Never Use",
        "keywords": "christmas present for dad (33,100/mo, KD 6) · christmas present for father (33,100/mo, KD 2) · father birthday gifts (33,100/mo, KD 9)",
        "why": "StoryWorth ranks #88-102 for these despite being the most obvious brand to own them. KD 2-9. Publish by late October to catch holiday traffic.",
    },
    {
        "title": "Voice vs. Text: Why Older Adults Remember More When They Speak Their Stories",
        "keywords": "autobiographical (60,500/mo, KD 21) · memory book (8,100/mo, KD 12)",
        "why": "Neither StoryWorth nor Remento covers the neuroscience of spoken vs. written memory. Listn's core product thesis. Earns backlinks from aging and caregiving publications.",
    },
    {
        "title": "What to Ask Your Parents Before It's Too Late: 50 Voice-Ready Questions for Recording Family Stories",
        "keywords": "get to know you questions (33,100/mo, KD 9) · memories books (8,100/mo, KD 0)",
        "why": "Remento's question content targets romantic relationships — irrelevant to their product. Listn can own intergenerational family storytelling questions. High shareability in caregiving communities.",
    },
]

KEYWORDS_TO_AVOID = [
    ("Romantic relationship questions",   "~10,400/mo", "Remento's top pages — heavy editorial investment. Completely irrelevant to Listn's audience."),
    ("iPhone photo scanning",             "~2,184/mo",  "A tech tutorial with zero conversion overlap with Listn users."),
    ("Autobiographical memory (generic)", "~657/mo",    "StoryWorth #9, Remento #23 already rank here. Attack via voice angle instead."),
    ("Mother's Day gift ideas (generic)", "~972/mo",    "Crowded, seasonal, dominated by large e-commerce players. Not defensible."),
]

# ── Helpers ────────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env_path = BASE.parent / ".env"
    if not env_path.exists():
        sys.exit(f"ERROR: .env not found at {env_path}")
    env = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def find_latest(pattern: str) -> Path:
    files = sorted(glob.glob(str(BASE / pattern)))
    if not files:
        sys.exit(f"ERROR: No file matching '{pattern}' in {BASE}/. Run seo_monitor.py first.")
    return Path(files[-1])


def strip_md(text: str) -> str:
    return re.sub(r"\*+|#+\s*", "", text).strip()

def esc(text: str) -> str:
    """Strip markdown then HTML-escape for safe embedding in ReportLab Paragraph XML."""
    return html.escape(strip_md(text))

# ── Load and filter quick wins ─────────────────────────────────────────────────
def load_quick_wins(raw: dict) -> list[dict]:
    rows = []
    seen = set()
    for comp, v in raw["competitors"].items():
        for kw in v["keywords"]:
            word = kw.get("keyword", "")
            vol  = int(kw.get("search_volume") or 0)
            kd   = int(kw.get("keyword_difficulty") or 0)
            pos  = int(kw.get("position") or 0)
            if word and word not in seen:
                seen.add(word)
                rows.append({"competitor": comp, "keyword": word,
                             "volume": vol, "kd": kd, "position": pos})

    # Primary filter: KD < 30, volume > 500, relevant
    filtered = [
        r for r in sorted(rows, key=lambda x: x["volume"], reverse=True)
        if r["kd"] < 30 and r["volume"] > 500 and is_relevant(r["keyword"])
    ]
    if len(filtered) < 5:
        filtered = sorted(rows, key=lambda x: x["kd"])[:10]
    return filtered[:10]

# ── Claude recommendations ─────────────────────────────────────────────────────
def get_recommendations(raw: dict, analysis_text: str, api_key: str) -> list[tuple]:
    kw_lines = []
    for comp, v in raw["competitors"].items():
        for k in v["keywords"][:5]:
            kw_lines.append(
                f"  {comp}: '{k['keyword']}' "
                f"vol={k.get('search_volume', 0):,} "
                f"pos={k.get('position', 0)} "
                f"kd={k.get('keyword_difficulty', 0)}"
            )

    user_msg = (
        f"Date: {raw['fetched_date']}\n\n"
        "Top competitor keywords this week:\n" + "\n".join(kw_lines) +
        f"\n\nFull analysis excerpt:\n{analysis_text[:6000]}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    print("Calling Claude for SEO recommendations...")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=(
            "You are an SEO strategist for Listn, a pre-launch voice-first memory app. "
            "Based on this week's competitor keyword data, generate 5 specific SEO "
            "recommendations for Listn's content team. Format each as: "
            "PRIORITY | RECOMMENDATION | WHY. "
            "Be specific to what the data shows this week — keyword opportunities, "
            "competitor weaknesses, content gaps to exploit now."
        ),
        messages=[{"role": "user", "content": user_msg}],
    )

    text = next((b.text for b in resp.content if b.type == "text"), "")
    recs = []
    for line in text.splitlines():
        line = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            priority = parts[0].upper().strip("* #")
            if priority in ("HIGH", "MEDIUM", "LOW"):
                recs.append((priority, parts[1].strip(), " | ".join(parts[2:]).strip()))
    if not recs:
        recs = [("HIGH", "SEO Strategy", strip_md(text[:700]))]
    print(f"  {len(recs)} recommendations received")
    return recs[:5]

# ── PDF builder ────────────────────────────────────────────────────────────────
def build_pdf(raw: dict, quick_wins: list[dict], recommendations: list[tuple]) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    PURPLE   = colors.HexColor("#4C1D95")
    LAVENDER = colors.HexColor("#A78BFA")
    LIGHT    = colors.HexColor("#F3F0FF")
    PALE     = colors.HexColor("#EDE9FE")
    RED_BG   = colors.HexColor("#FEF2F2")
    RED_HEAD = colors.HexColor("#991B1B")

    T_style  = ParagraphStyle("T2",  parent=styles["Title"],   textColor=PURPLE,   fontSize=20, spaceAfter=4)
    H_style  = ParagraphStyle("H2x", parent=styles["Heading2"],textColor=PURPLE,   fontSize=12, spaceBefore=14, spaceAfter=5)
    B_style  = ParagraphStyle("B2",  parent=styles["Normal"],  fontSize=9,  leading=13)
    C_style  = ParagraphStyle("Cap", parent=styles["Normal"],  fontSize=8,  textColor=colors.grey, leading=12)
    SM_style = ParagraphStyle("SM",  parent=styles["Normal"],  fontSize=8,  leading=12)
    IT_style = ParagraphStyle("IT",  parent=styles["Normal"],  fontSize=8,  leading=12,
                              textColor=colors.HexColor("#4B5563"))

    report_date = date.today().strftime("%B %d, %Y")
    fetched     = raw.get("fetched_date", report_date)
    story       = []

    # ── Title ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("Listn SEO Intelligence", T_style))
    story.append(Paragraph(
        f"Week of {report_date} &nbsp;·&nbsp; DataForSEO &nbsp;·&nbsp; "
        f"Data fetched: {fetched}", C_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=LAVENDER, spaceAfter=10))

    # ── Section 1: Quick Win Keywords ──────────────────────────────────────────
    story.append(Paragraph("Section 1 — Quick Win Keywords", H_style))
    story.append(Paragraph(
        f"<i>Filtered: KD &lt; 30 · Volume &gt; 500 · Listn-relevant only"
        f" · {len(quick_wins)} keywords · sorted by volume</i>", C_style,
    ))
    story.append(Spacer(1, 0.07*inch))

    qw_data = [[
        Paragraph("<b>Keyword</b>", SM_style),
        Paragraph("<b>Volume/mo</b>", SM_style),
        Paragraph("<b>KD</b>", SM_style),
        Paragraph("<b>Top Competitor</b>", SM_style),
        Paragraph("<b>Listn's Edge</b>", SM_style),
    ]]
    for r in quick_wins:
        qw_data.append([
            Paragraph(r["keyword"], SM_style),
            Paragraph(f"{r['volume']:,}", SM_style),
            Paragraph(str(r["kd"]), SM_style),
            Paragraph(r["competitor"], SM_style),
            Paragraph(edge_for(r["keyword"]), IT_style),
        ])

    t1 = Table(
        qw_data,
        colWidths=[1.6*inch, 0.75*inch, 0.4*inch, 0.95*inch, 2.8*inch],
        repeatRows=1,
    )
    t1.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  PURPLE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#C4B5FD")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]))
    story.append(t1)
    story.append(Spacer(1, 0.1*inch))

    # ── Section 2: Content Roadmap ─────────────────────────────────────────────
    story.append(Paragraph("Section 2 — Top 5 Content Pieces to Write Before Launch", H_style))
    story.append(Spacer(1, 0.04*inch))

    for i, post in enumerate(BLOG_POSTS, 1):
        inner = Table(
            [[
                Paragraph(f"<b>{i}</b>", ParagraphStyle(
                    "num", fontSize=15, textColor=LAVENDER, alignment=1,
                )),
                [
                    Paragraph(f"<b>{esc(post['title'])}</b>", B_style),
                    Spacer(1, 0.03*inch),
                    Paragraph(
                        f"<b>Keywords:</b> {esc(post['keywords'])}", SM_style,
                    ),
                    Spacer(1, 0.02*inch),
                    Paragraph(
                        f"<i>Why: {esc(post['why'])}</i>", IT_style,
                    ),
                ],
            ]],
            colWidths=[0.4*inch, 6.1*inch],
        )
        inner.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND",   (0, 0), (-1, -1), PALE),
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#DDD6FE")),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ]))
        story.append(inner)
        story.append(Spacer(1, 0.045*inch))

    story.append(Spacer(1, 0.04*inch))

    # ── Section 3: Claude Recommendations ─────────────────────────────────────
    story.append(Paragraph("Section 3 — This Week's SEO Recommendations", H_style))
    story.append(Paragraph(
        "<i>Generated by Claude AI from this week's live keyword data</i>", C_style,
    ))
    story.append(Spacer(1, 0.07*inch))

    for priority, title, detail in recommendations:
        pill_bg = PURPLE if priority == "HIGH" else colors.HexColor("#6D28D9")
        rec = Table(
            [[
                Paragraph(f"<b>{priority}</b>", ParagraphStyle(
                    "pill", fontSize=7, textColor=colors.white,
                    backColor=pill_bg, borderPadding=2,
                )),
                Paragraph(
                    f"<b>{esc(title)}</b><br/>"
                    f"<font size=8 color='#374151'>{esc(detail)}</font>",
                    B_style,
                ),
            ]],
            colWidths=[0.6*inch, 5.9*inch],
        )
        rec.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#C4B5FD")),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (1, 0), (1, -1),  8),
        ]))
        story.append(rec)
        story.append(Spacer(1, 0.045*inch))

    story.append(Spacer(1, 0.04*inch))

    # ── Section 4: Keywords to Avoid ──────────────────────────────────────────
    story.append(Paragraph("Section 4 — Keywords to Avoid This Week", H_style))
    story.append(Paragraph(
        "<i>Competitor clusters with irrelevant audiences — do not chase these</i>", C_style,
    ))
    story.append(Spacer(1, 0.07*inch))

    avoid_data = [[
        Paragraph("<b>Cluster</b>", SM_style),
        Paragraph("<b>Est. Traffic</b>", SM_style),
        Paragraph("<b>Why Avoid</b>", SM_style),
    ]]
    for cluster, traffic, why in KEYWORDS_TO_AVOID:
        avoid_data.append([
            Paragraph(f"<b>{cluster}</b>", SM_style),
            Paragraph(traffic, SM_style),
            Paragraph(why, IT_style),
        ])

    t4 = Table(
        avoid_data,
        colWidths=[2.0*inch, 0.85*inch, 3.65*inch],
        repeatRows=1,
    )
    t4.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  RED_HEAD),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [RED_BG, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#FECACA")),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ]))
    story.append(t4)

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#C4B5FD")))
    story.append(Spacer(1, 0.06*inch))
    story.append(Paragraph(
        f"Generated automatically · Listn SEO Intelligence · "
        f"DataForSEO + claude-sonnet-4-6 · {report_date}",
        C_style,
    ))

    doc.build(story)
    return buf.getvalue()

# ── Email ──────────────────────────────────────────────────────────────────────
def send_email(pdf_bytes: bytes, sender: str, password: str) -> str:
    date_str = date.today().strftime("%Y-%m-%d")
    subject  = f"Listn SEO Intel — Week of {date_str}"
    filename = f"listn_seo_report_{date_str}.pdf"

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(
        "Weekly SEO intelligence report is attached.\n\n"
        "Sections:\n"
        "  1. Quick Win Keywords (KD<30, volume>500, Listn-relevant)\n"
        "  2. Top 5 Content Pieces to Write Before Launch\n"
        "  3. This Week's Claude-Generated SEO Recommendations\n"
        "  4. Keywords to Avoid\n\n"
        "Generated automatically from DataForSEO competitor data.",
        "plain",
    ))
    part = MIMEBase("application", "octet-stream")
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    print("Connecting to smtp.gmail.com:587...")
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        print(f"Logging in as {sender}...")
        server.login(sender, password)
        server.sendmail(sender, RECIPIENT, msg.as_string())

    local = BASE.parent / filename
    local.write_bytes(pdf_bytes)
    print(f"PDF saved: {local}")
    return filename

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    env      = load_env()
    sender   = env.get("EMAIL_SENDER",    "").strip()
    password = env.get("EMAIL_PASSWORD",  "").strip()
    api_key  = env.get("ANTHROPIC_API_KEY","").strip()

    if not sender:   sys.exit("ERROR: EMAIL_SENDER not set in .env")
    if not password: sys.exit("ERROR: EMAIL_PASSWORD not set in .env")
    if not api_key:  sys.exit("ERROR: ANTHROPIC_API_KEY not set in .env")

    raw_path      = find_latest("seo_raw_*.json")
    analysis_path = find_latest("seo_analysis_*.md")
    print(f"Raw data:  {raw_path.name}")
    print(f"Analysis:  {analysis_path.name}")

    with open(raw_path) as f:
        raw = json.load(f)
    analysis_text = analysis_path.read_text()

    print("Filtering quick win keywords...")
    quick_wins = load_quick_wins(raw)
    print(f"  {len(quick_wins)} quick wins found")

    recommendations = get_recommendations(raw, analysis_text, api_key)

    print("Building PDF...")
    pdf_bytes = build_pdf(raw, quick_wins, recommendations)
    print(f"  {len(pdf_bytes):,} bytes")

    try:
        filename = send_email(pdf_bytes, sender, password)
        print(f"\n✓ Email sent to {RECIPIENT}")
        print(f"  Subject: {filename.replace('_', ' ').replace('.pdf', '')}")
        print(f"  Attachment: {filename}")
    except smtplib.SMTPAuthenticationError:
        sys.exit(
            "\nERROR: Gmail auth failed.\n"
            "Use a 16-char App Password from https://myaccount.google.com/apppasswords"
        )
    except Exception as exc:
        sys.exit(f"\nERROR sending email: {exc}")
