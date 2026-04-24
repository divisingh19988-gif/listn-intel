"""
Competitor SEO intelligence monitor using DataForSEO Labs API.
Fetches ranked keywords, positions, volumes, and difficulty for each competitor.
Saves results to seo_raw_YYYY-MM-DD.json.
"""

import os
import json
import sys
import requests
from datetime import date
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

OUTPUT_DIR = os.path.dirname(__file__)
LOCATION_CODE = 2840  # United States
LANGUAGE_CODE = "en"
KEYWORD_LIMIT = 30

COMPETITORS = {
    "Remento": "remento.co",
    "Meminto": "meminto.com",
    "StoryWorth": "storyworth.com",
    "Storykeeper": "storykeeper.com",
}

CTR_BY_POSITION = {1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.06,
                   6: 0.05, 7: 0.04, 8: 0.03, 9: 0.03, 10: 0.025}


def get_auth() -> tuple[str, str]:
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    if not login or not password:
        print("ERROR: DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD must be set in .env")
        sys.exit(1)
    return (login, password)


def api_post(endpoint: str, payload: list) -> dict:
    url = f"https://api.dataforseo.com/v3/{endpoint}"
    resp = requests.post(url, json=payload, auth=get_auth(), timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_ranked_keywords(domain: str) -> list[dict]:
    payload = [{
        "target": domain,
        "language_code": LANGUAGE_CODE,
        "location_code": LOCATION_CODE,
        "limit": KEYWORD_LIMIT,
        "order_by": ["keyword_data.keyword_info.search_volume,desc"],
    }]

    result = api_post("dataforseo_labs/google/ranked_keywords/live", payload)

    task = result.get("tasks", [{}])[0]
    status_code = task.get("status_code", 0)
    if status_code != 20000:
        print(f"  API task error {status_code}: {task.get('status_message', '')}")
        return []

    keywords = []
    try:
        items = task["result"][0]["items"] or []
        for item in items:
            kw_data = item.get("keyword_data", {})
            kw_info = kw_data.get("keyword_info", {})
            kw_props = kw_data.get("keyword_properties", {})
            serp_item = item.get("ranked_serp_element", {}).get("serp_item", {})

            keywords.append({
                "keyword": kw_data.get("keyword", ""),
                "search_volume": kw_info.get("search_volume") or 0,
                "position": serp_item.get("rank_absolute") or 0,
                "keyword_difficulty": kw_props.get("keyword_difficulty") or 0,
                "url": serp_item.get("url", ""),
            })
    except (KeyError, IndexError, TypeError) as exc:
        print(f"  Warning: parse error — {exc}")

    return keywords


def derive_top_pages(keywords: list[dict], top_n: int = 10) -> list[dict]:
    """Group ranking URLs and estimate monthly organic traffic via CTR model."""
    pages: dict[str, dict] = defaultdict(
        lambda: {"estimated_traffic": 0, "keyword_count": 0, "sample_keywords": []}
    )

    for kw in keywords:
        url = kw.get("url", "").strip()
        if not url:
            continue
        volume = kw.get("search_volume") or 0
        pos = kw.get("position") or 100
        ctr = CTR_BY_POSITION.get(pos, max(0.005, 0.25 / pos))
        pages[url]["estimated_traffic"] += int(volume * ctr)
        pages[url]["keyword_count"] += 1
        if len(pages[url]["sample_keywords"]) < 5:
            pages[url]["sample_keywords"].append(kw["keyword"])

    ranked = sorted(pages.items(), key=lambda x: x[1]["estimated_traffic"], reverse=True)
    return [{"url": url, **stats} for url, stats in ranked[:top_n]]


def run():
    today = date.today().isoformat()
    output_file = os.path.join(OUTPUT_DIR, f"seo_raw_{today}.json")

    all_data = {"fetched_date": today, "competitors": {}}

    for name, domain in COMPETITORS.items():
        print(f"\nFetching '{name}' ({domain})...")
        keywords = fetch_ranked_keywords(domain)
        top_pages = derive_top_pages(keywords)

        print(f"  Keywords: {len(keywords)}")
        print(f"  Top pages derived: {len(top_pages)}")
        if keywords:
            k = keywords[0]
            print(f"  Top keyword: '{k['keyword']}' | vol: {k['search_volume']:,} | pos: {k['position']} | diff: {k['keyword_difficulty']}")

        all_data["competitors"][name] = {
            "domain": domain,
            "keywords": keywords,
            "top_pages": top_pages,
        }

    with open(output_file, "w") as f:
        json.dump(all_data, f, indent=2)

    total_kw = sum(len(v["keywords"]) for v in all_data["competitors"].values())
    print(f"\n{'='*60}")
    print(f"✓ Saved to {output_file}")
    print(f"  Total keywords fetched: {total_kw}")
    print(f"  Competitors covered: {', '.join(COMPETITORS)}")


if __name__ == "__main__":
    run()
