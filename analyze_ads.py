"""
Competitor ad intelligence analysis using Claude API.
Reads scraped ad data and produces a strategic markdown report.
"""

import os
import json
from datetime import date
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

INPUT_FILE = "ads_scraped_2026-04-23.json"
OUTPUT_FILE = "competitor_analysis.md"
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You are a growth strategist for Listn, a voice-first memory preservation app for older adults \
that lets family members capture and preserve the life stories of their loved ones through \
guided voice conversations — no writing required.

Analyze the competitor Meta ad data provided and produce a comprehensive strategic report covering:

1. **Messaging Themes** — What core messages and value propositions each competitor uses in their ads
2. **Longevity Analysis** — Which ads have run the longest, with days_running data, and why those \
specific creatives keep working
3. **CTA Landscape** — What calls-to-action dominate the space; which are most common vs. most \
distinctive
4. **Emotional Tone** — The emotional register each brand operates in (e.g. nostalgia, urgency, \
warmth, fear of loss, celebration)
5. **3 Things Listn Should Do Differently** — Specific, actionable recommendations based on \
gaps or weaknesses you observe in competitor ads
6. **Gaps Listn Can Own** — Underserved angles, audiences, or emotional territories competitors \
are ignoring that Listn can claim

Format your response as a polished markdown document with:
- Clear section headers (##)
- Per-competitor breakdowns using tables or bullet points
- Specific ad copy quoted directly from the data (use > blockquotes)
- Concrete, opinionated recommendations — not hedged generalities
"""


def load_ad_data() -> dict:
    with open(INPUT_FILE) as f:
        return json.load(f)


def prepare_payload(data: dict) -> str:
    """Build a clean, token-efficient representation of the ad data for the prompt."""
    payload = {
        "fetched_date": data["fetched_date"],
        "competitors": {},
    }
    for competitor, ads in data["competitors"].items():
        # Keep only ads with actual content; cap per competitor to manage token count
        rich = [
            {k: v for k, v in ad.items() if v and k != "competitor"}
            for ad in ads
            if ad.get("ad_copy") or ad.get("headline")
        ]
        if rich:
            payload["competitors"][competitor] = rich[:40]

    return json.dumps(payload, indent=2)


def run_analysis():
    print(f"Loading ad data from {INPUT_FILE}...")
    data = load_ad_data()

    total = data.get("total_ads", 0)
    with_content = sum(
        1 for ads in data["competitors"].values()
        for ad in ads
        if ad.get("ad_copy") or ad.get("headline")
    )
    print(f"  {total} total ads, {with_content} with ad copy")

    payload_str = prepare_payload(data)
    print(f"  Payload size: {len(payload_str):,} chars")
    print(f"\nSending to {MODEL} for analysis (streaming)...\n")
    print("=" * 60)

    chunks = []

    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Here is the Meta ad data scraped from the Ad Library "
                            f"on {data['fetched_date']}:\n\n"
                            f"```json\n{payload_str}\n```\n\n"
                            "Please produce the full strategic analysis now."
                        ),
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            chunks.append(text)
        final_msg = stream.get_final_message()

    print("\n" + "=" * 60)

    analysis = "".join(chunks)

    # Prepend a header with metadata
    header = (
        f"# Listn — Competitor Ad Intelligence Report\n\n"
        f"**Generated:** {date.today().isoformat()}  \n"
        f"**Data source:** `{INPUT_FILE}`  \n"
        f"**Model:** `{MODEL}`  \n\n"
        "---\n\n"
    )

    with open(OUTPUT_FILE, "w") as f:
        f.write(header + analysis)

    usage = final_msg.usage
    print(f"\n✓ Saved to {OUTPUT_FILE}")
    print(f"  Input tokens:  {usage.input_tokens:,}")
    print(f"  Output tokens: {usage.output_tokens:,}")
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    if cache_read or cache_write:
        print(f"  Cache read:    {cache_read:,}")
        print(f"  Cache write:   {cache_write:,}")


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set in .env")
    else:
        run_analysis()
