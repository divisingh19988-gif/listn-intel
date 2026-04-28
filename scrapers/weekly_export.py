"""
Weekly export — build 3 Excel reports + email them via Resend.

Run after Meta + SEO + AI scrapers have refreshed data/.
Used by .github/workflows/weekly_refresh.yml on Mon 12:00 UTC.

Behavior:
  1. Build 3 Excel files for current ISO week (lib/excel_export).
  2. Pull "This Week's Moves" headline (lib/synthesis) for the email body.
  3. Send via Resend with the 3 files attached.

Required env / secrets:
  RESEND_API_KEY, REPORT_EMAIL    (mandatory for sending)
  ANTHROPIC_API_KEY               (optional — only if you regenerate analysis)

If RESEND_API_KEY is missing the script still builds the reports but skips
sending and exits 0, so the GitHub Actions step doesn't fail.
"""

from __future__ import annotations

import base64
import os
import sys
from datetime import datetime
from pathlib import Path

# Allow `from lib...` from the repo root regardless of where we run from.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from lib.excel_export import build_all_reports
from lib.supabase_client import current_iso_week
from lib.synthesis import (
    get_creative_move,
    get_content_move,
    count_new_ads_this_week,
    next_deadline,
)

REPORT_EMAIL_DEFAULT = "digvijayudawat064@gmail.com"
FROM_EMAIL_DEFAULT = "onboarding@resend.dev"  # Resend's verified sandbox sender


def _read_secret(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def _build_email_body(week_label: str) -> str:
    creative = get_creative_move()
    content = get_content_move()
    new_ads = count_new_ads_this_week()
    deadline = next_deadline()

    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background:#0F1117; color:#F0F0F0; padding:24px; }}
    .card {{ background:#1C1E26; border:1px solid #2A2D3A; border-radius:12px;
             padding:18px 22px; margin-bottom:16px; }}
    .accent {{ border-left:4px solid #4F8EF7; }}
    .urgent {{ border-left:4px solid #E5534B; }}
    h1 {{ color:#F0F0F0; margin:0 0 6px; font-size:1.4rem; }}
    .muted {{ color:#8B8FA8; font-size:0.85rem; }}
    .label {{ color:#8B8FA8; font-size:0.7rem; letter-spacing:0.1em;
              text-transform:uppercase; font-weight:700; margin-bottom:4px; }}
    .stat {{ display:inline-block; margin-right:24px; }}
    .stat-value {{ font-size:1.6rem; font-weight:800; color:#4F8EF7; }}
  </style>
</head>
<body>
  <h1>Listn Intel · {week_label}</h1>
  <p class="muted">Two moves for the week. Pulled live from Meta + SEO data.</p>

  <div class="card accent">
    <div class="label">🎯 Creative move</div>
    <p><strong>Do this:</strong> {creative['do']}</p>
    <p><strong>Because:</strong> {creative['because']}</p>
    <p class="muted"><em>{creative.get('source_ref', '')}</em></p>
  </div>

  <div class="card urgent">
    <div class="label">📝 Content move · {content.get('cluster', '')}</div>
    <p><strong>Do this:</strong> {content['do']}</p>
    <p><strong>Because:</strong> {content['because']}</p>
    <p class="muted">Volume {content['volume']:,}/mo · KD {content['kd']}</p>
  </div>

  <div class="card">
    <div class="label">Supporting stats</div>
    <div class="stat"><div class="stat-value">{new_ads}</div><div class="muted">New competitor ads (7d)</div></div>
    <div class="stat"><div class="stat-value">{deadline['label']}</div><div class="muted">Next deadline</div></div>
  </div>

  <p class="muted">
    Three Excel files are attached: Meta Intel, SEO Intel, AI Readiness.
    Each has Summary / Raw / Delta sheets.
  </p>
  <p class="muted">— Listn Intel automation · {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</body>
</html>
"""


def main() -> int:
    week = current_iso_week()
    print(f"Building reports for {week}…")
    paths = build_all_reports(week)
    for kind, path in paths.items():
        size_kb = path.stat().st_size / 1024
        print(f"  · {kind:5s}  {path.name}  ({size_kb:.0f} KB)")

    api_key = _read_secret("RESEND_API_KEY")
    to_email = _read_secret("REPORT_EMAIL", REPORT_EMAIL_DEFAULT)
    from_email = _read_secret("RESEND_FROM_EMAIL", FROM_EMAIL_DEFAULT)

    if not api_key:
        print(
            "\nRESEND_API_KEY not set — skipping email send. "
            "Reports were still built and saved in reports/."
        )
        return 0

    try:
        import resend  # type: ignore
    except ImportError:
        print("ERROR: 'resend' package is not installed.")
        return 1

    resend.api_key = api_key
    attachments = []
    for path in paths.values():
        with open(path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()
        attachments.append({
            "filename": path.name,
            "content": content_b64,
        })

    subject = f"Listn Intel · {week}"
    print(f"\nSending email '{subject}' to {to_email} from {from_email}…")
    try:
        params = {
            "from": f"Listn Intel <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": _build_email_body(week),
            "attachments": attachments,
        }
        resp = resend.Emails.send(params)
        print(f"  Sent. id={resp.get('id') if isinstance(resp, dict) else resp}")
    except Exception as e:
        print(f"  Email send failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
