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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

BASE = Path(__file__).parent
RECIPIENT = "digvijayudawat064@gmail.com"

# ── Load .env ─────────────────────────────────────────────────────────────────
def load_env():
    env = {}
    env_path = BASE / ".env"
    if not env_path.exists():
        sys.exit("ERROR: .env file not found")
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

# ── Load ad data ──────────────────────────────────────────────────────────────
def load_data():
    path = BASE / "ads_scraped_2026-04-23.json"
    if not path.exists():
        sys.exit("ERROR: ads_scraped_2026-04-23.json not found")
    with open(path) as f:
        return json.load(f)

# ── Load competitor analysis ──────────────────────────────────────────────────
def load_competition_md():
    path = BASE / "competitor_analysis.md"
    if not path.exists():
        return ""
    return path.read_text()

# ── Generate recommendations via Claude API ───────────────────────────────────
def generate_recommendations(raw, competition_text, api_key):
    # Build a compact ad-data summary to send alongside the full analysis
    summary_lines = []
    for comp, ads in raw["competitors"].items():
        if not ads:
            continue
        active = sum(1 for a in ads if a.get("stop_date") is None)
        total  = len(ads)
        newest = max(ads, key=lambda a: a.get("start_date") or "", default=None)
        summary_lines.append(f"- {comp}: {total} total ads, {active} active")
        if newest:
            snippet = (newest.get("ad_copy") or "").strip()[:120]
            if snippet:
                summary_lines.append(f'  Latest ad copy: "{snippet}"')

    ad_summary = "\n".join(summary_lines)

    user_content = (
        "## This Week's Competitor Ad Data\n\n"
        f"{ad_summary}\n\n"
        "## Full Competitor Analysis Report\n\n"
        f"{competition_text}"
    )

    client = anthropic.Anthropic(api_key=api_key)

    print("Calling Claude API for strategic recommendations ...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=(
            "You are a growth strategist for Listn, a voice-first memory app. "
            "Based on this week's competitor ad data, generate 5 specific strategic "
            "recommendations for Listn's marketing team. Format each as: "
            "PRIORITY | RECOMMENDATION | WHY. "
            "Be specific to what changed this week, not generic advice."
        ),
        messages=[{"role": "user", "content": user_content}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")

    recommendations = []
    for line in text.splitlines():
        line = line.strip()
        # Strip leading list markers like "1." or "1)"
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            priority = parts[0].upper().strip("* ")
            if priority in ("HIGH", "MEDIUM", "LOW"):
                title  = parts[1].strip()
                detail = " | ".join(parts[2:]).strip()
                recommendations.append((priority, title, detail))

    if not recommendations:
        # Fallback: surface raw Claude output as a single recommendation
        recommendations = [("HIGH", "Strategic Analysis", text[:500])]

    return recommendations[:5]

# ── Build PDF ─────────────────────────────────────────────────────────────────
def build_pdf(raw, recommendations):
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    PURPLE   = colors.HexColor("#4C1D95")
    LAVENDER = colors.HexColor("#A78BFA")
    LIGHT    = colors.HexColor("#F3F0FF")

    title_style = ParagraphStyle(
        "Title2", parent=styles["Title"],
        textColor=PURPLE, fontSize=20, spaceAfter=4,
    )
    heading_style = ParagraphStyle(
        "Heading2x", parent=styles["Heading2"],
        textColor=PURPLE, fontSize=13, spaceBefore=14, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body2", parent=styles["Normal"],
        fontSize=9, leading=14,
    )
    caption_style = ParagraphStyle(
        "Caption", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey, leading=12,
    )

    story = []

    # ── Title block ────────────────────────────────────────────────────────────
    report_date = date.today().strftime("%B %d, %Y")
    story.append(Paragraph("Listn Competitor Intelligence", title_style))
    story.append(Paragraph(f"Weekly Report &nbsp;·&nbsp; {report_date}", caption_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=LAVENDER, spaceAfter=10))

    # ── KPI summary ────────────────────────────────────────────────────────────
    story.append(Paragraph("Competitor Ad Count Summary", heading_style))

    all_ads = []
    for ads in raw["competitors"].values():
        all_ads.extend(ads)

    comp_stats = []
    for comp, ads in raw["competitors"].items():
        if not ads:
            continue
        active = sum(1 for a in ads if a.get("stop_date") is None)
        total  = len(ads)
        comp_stats.append((comp, total, active, total - active))

    comp_stats.sort(key=lambda x: x[1], reverse=True)

    header_row = ["Competitor", "Total Ads", "Active", "Stopped"]
    table_data  = [header_row] + [list(r) for r in comp_stats]
    totals_row  = [
        "TOTAL",
        sum(r[1] for r in comp_stats),
        sum(r[2] for r in comp_stats),
        sum(r[3] for r in comp_stats),
    ]
    table_data.append(totals_row)

    t = Table(table_data, colWidths=[2.8*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  PURPLE),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  9),
        ("BACKGROUND",  (0, 1), (-1, -2), LIGHT),
        ("BACKGROUND",  (0, -1), (-1, -1), colors.HexColor("#DDD6FE")),
        ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#C4B5FD")),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [LIGHT, colors.white]),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # ── Top 5 longest-running ads ──────────────────────────────────────────────
    story.append(Paragraph("Top 5 Longest-Running Ads", heading_style))

    sorted_ads = sorted(all_ads, key=lambda a: a.get("days_running") or 0, reverse=True)[:5]

    cell_style = ParagraphStyle(
        "Cell", parent=styles["Normal"],
        fontSize=8, leading=11,
    )

    top_header = ["Competitor", "Days", "Status", "Ad Copy"]
    top_data   = [top_header]
    for ad in sorted_ads:
        copy   = (ad.get("ad_copy") or "").strip()
        status = "Active" if ad.get("stop_date") is None else "Stopped"
        top_data.append([
            ad.get("competitor", ""),
            str(ad.get("days_running", 0)),
            status,
            Paragraph(copy, cell_style),
        ])

    t2 = Table(top_data, colWidths=[1.1*inch, 0.55*inch, 0.65*inch, 250],
               rowHeights=None)
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#C4B5FD")),
        ("BACKGROUND", (0, 1), (-1, -1), LIGHT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, colors.white]),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.15*inch))

    # ── Strategic recommendations (Claude-generated) ───────────────────────────
    story.append(Paragraph("Key Strategic Recommendations for Listn", heading_style))
    story.append(Paragraph(
        "<i>Generated by Claude AI based on this week's ad data</i>",
        caption_style,
    ))
    story.append(Spacer(1, 0.06*inch))

    def strip_md(text):
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"#+\s*", "", text)
        return text.strip()

    for priority, title, detail in recommendations:
        clean_title  = strip_md(title)
        clean_detail = strip_md(detail)
        pill_color = PURPLE if priority == "HIGH" else colors.HexColor("#6D28D9")
        rec_table = Table(
            [[
                Paragraph(f"<b>{priority}</b>", ParagraphStyle(
                    "pill", fontSize=7, textColor=colors.white,
                    backColor=pill_color, borderPadding=2,
                )),
                Paragraph(f"<b>{clean_title}</b><br/><font size=8>{clean_detail}</font>", body_style),
            ]],
            colWidths=[0.55*inch, 5.9*inch],
        )
        rec_table.setStyle(TableStyle([
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, -1),  4),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 0.06*inch))

    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#C4B5FD")))
    story.append(Spacer(1, 0.08*inch))
    story.append(Paragraph(
        f"Generated automatically from Meta Ad Library data &nbsp;·&nbsp; {report_date}",
        caption_style,
    ))

    doc.build(story)
    return buf.getvalue()

# ── Send email ────────────────────────────────────────────────────────────────
def send(pdf_bytes, sender, password):
    date_str  = date.today().strftime("%Y-%m-%d")
    subject   = f"Listn Competitor Intel — Week of {date_str}"
    filename  = f"listn_weekly_report_{date_str}.pdf"

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(
        "Weekly competitor intelligence report attached.\n"
        "Generated automatically from Meta Ad Library data.",
        "plain",
    ))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    print(f"Connecting to smtp.gmail.com:587 ...")
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        print(f"Logging in as {sender} ...")
        server.login(sender, password)
        server.sendmail(sender, RECIPIENT, msg.as_string())

    # Save a local copy too
    local_copy = BASE / filename
    local_copy.write_bytes(pdf_bytes)
    print(f"PDF saved locally: {local_copy.name}")
    return filename

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    env = load_env()

    sender   = env.get("EMAIL_SENDER", "").strip()
    password = env.get("EMAIL_PASSWORD", "").strip()
    api_key  = env.get("ANTHROPIC_API_KEY", "").strip()

    if not sender:
        sys.exit("ERROR: EMAIL_SENDER is not set in .env")
    if not password:
        sys.exit("ERROR: EMAIL_PASSWORD is not set in .env")
    if not api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY is not set in .env")

    print("Loading ad data ...")
    raw = load_data()

    print("Loading competitor analysis ...")
    competition_text = load_competition_md()

    print("Generating strategic recommendations via Claude API ...")
    recommendations = generate_recommendations(raw, competition_text, api_key)
    print(f"Received {len(recommendations)} recommendations from Claude")

    print("Generating PDF ...")
    pdf_bytes = build_pdf(raw, recommendations)
    print(f"PDF generated ({len(pdf_bytes):,} bytes)")

    try:
        filename = send(pdf_bytes, sender, password)
        print(f"\nSUCCESS — email sent to {RECIPIENT}")
        print(f"Subject: Listn Competitor Intel — Week of {date.today().strftime('%Y-%m-%d')}")
        print(f"Attachment: {filename}")
    except smtplib.SMTPAuthenticationError:
        sys.exit(
            "\nERROR: Gmail authentication failed.\n"
            "Make sure EMAIL_PASSWORD in .env is a Gmail App Password (16 chars, no spaces),\n"
            "not your regular Gmail password. Generate one at:\n"
            "  https://myaccount.google.com/apppasswords"
        )
    except Exception as e:
        sys.exit(f"\nERROR: {e}")
