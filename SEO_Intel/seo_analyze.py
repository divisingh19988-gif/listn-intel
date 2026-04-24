"""
SEO competitive analysis for Listn using Claude.
Reads the latest seo_raw JSON and produces a strategic markdown report.
"""

import os
import json
import glob
from datetime import date
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

INPUT_DIR = os.path.dirname(__file__)
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
You are an SEO strategist for Listn, a pre-launch voice-first memory app for older adults. \
Analyze this competitor keyword data and tell me:
1. Top 10 keywords Listn should target first (lowest difficulty, decent volume)
2. Top 5 blog posts Listn should write before launch with suggested titles and why
3. What content gaps exist that no competitor has covered
4. What keyword clusters Remento owns that Listn should avoid initially
5. Quick wins — keywords under difficulty 30 with over 500 monthly searches

Format your response as a polished markdown document with clear section headers (##), \
tables where appropriate, and concrete opinionated recommendations — not hedged generalities.\
"""

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def find_latest_raw_file() -> str:
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "seo_raw_*.json")))
    if not files:
        raise FileNotFoundError(f"No seo_raw_*.json files found in {INPUT_DIR}/")
    return files[-1]


def build_payload(data: dict) -> str:
    summary = {"fetched_date": data["fetched_date"], "competitors": {}}
    for name, comp in data["competitors"].items():
        summary["competitors"][name] = {
            "domain": comp["domain"],
            "keywords": comp["keywords"],
            "top_pages": comp.get("top_pages", [])[:8],
        }
    return json.dumps(summary, indent=2)


def run():
    input_file = find_latest_raw_file()
    print(f"Loading SEO data from {input_file}...")

    with open(input_file) as f:
        data = json.load(f)

    total_kw = sum(len(v["keywords"]) for v in data["competitors"].values())
    print(f"  {total_kw} keywords across {len(data['competitors'])} competitors")

    payload_str = build_payload(data)
    print(f"  Payload: {len(payload_str):,} chars")
    print(f"\nSending to {MODEL} for SEO analysis (streaming)...\n")
    print("=" * 60)

    chunks = []

    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": [{
                "type": "text",
                "text": (
                    f"Here is the competitor SEO data fetched on {data['fetched_date']}:\n\n"
                    f"```json\n{payload_str}\n```\n\n"
                    "Please produce the full SEO strategy analysis now."
                ),
                "cache_control": {"type": "ephemeral"},
            }],
        }],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            chunks.append(text)
        final_msg = stream.get_final_message()

    print("\n" + "=" * 60)

    analysis = "".join(chunks)
    today = date.today().isoformat()
    output_file = os.path.join(INPUT_DIR, f"seo_analysis_{today}.md")

    header = (
        f"# Listn — Competitor SEO Intelligence Report\n\n"
        f"**Generated:** {today}  \n"
        f"**Data source:** `{os.path.basename(input_file)}`  \n"
        f"**Model:** `{MODEL}`  \n\n"
        "---\n\n"
    )

    with open(output_file, "w") as f:
        f.write(header + analysis)

    usage = final_msg.usage
    print(f"\n✓ Saved to {output_file}")
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
        run()
