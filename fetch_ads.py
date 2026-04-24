import os
import json
import time
import requests
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

META_TOKEN = os.getenv("META_TOKEN")

COMPETITORS = [
    "Remento",
    "Meminto",
    "StoryWorth",
    "Storykeeper",
    "Tell me",
    "Keepsake",
    "HereAfter AI",
    "No Story Lost",
]

AD_LIBRARY_URL = "https://graph.facebook.com/v19.0/ads_archive"
GRAPH_BASE = "https://graph.facebook.com/v19.0"


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

def validate_token() -> bool:
    """Check that the token is alive and has ads_read permission."""
    print("Validating token...")

    # 1. Basic identity check
    resp = requests.get(f"{GRAPH_BASE}/me", params={"access_token": META_TOKEN})
    if resp.status_code != 200:
        err = resp.json().get("error", {})
        code = err.get("code")
        msg = err.get("message", "unknown error")

        if code == 190:
            print("\n  TOKEN ERROR: Your token has expired or is invalid.")
            print("  Get a fresh token from Graph API Explorer:")
            print("  https://developers.facebook.com/tools/explorer/")
            print("  Steps:")
            print("    1. Select your app in the top-right dropdown")
            print("    2. Click 'Generate Access Token'")
            print("    3. Check the 'ads_read' permission box")
            print("    4. Approve in the pop-up")
            print("    5. Paste the new token into .env as META_TOKEN=")
        else:
            print(f"\n  TOKEN ERROR ({code}): {msg}")
        return False

    me = resp.json()
    print(f"  Token is valid. Authenticated as: {me.get('name', me.get('id'))}")

    # 2. Check permissions
    perm_resp = requests.get(
        f"{GRAPH_BASE}/me/permissions",
        params={"access_token": META_TOKEN},
    )
    if perm_resp.status_code == 200:
        permissions = {
            p["permission"]: p["status"]
            for p in perm_resp.json().get("data", [])
        }
        ads_read_status = permissions.get("ads_read", "missing")

        if ads_read_status == "granted":
            print("  Permission 'ads_read': GRANTED")
        else:
            print(f"\n  PERMISSION ERROR: 'ads_read' is {ads_read_status}.")
            print("  Your token is missing the 'ads_read' permission.")
            print("\n  How to fix:")
            print("  1. Go to https://developers.facebook.com/tools/explorer/")
            print("  2. Select your app in the top-right dropdown")
            print("  3. Click 'Generate Access Token'")
            print("  4. In the permissions panel, search for and check 'ads_read'")
            print("  5. Click Generate, approve in the pop-up")
            print("  6. Copy the token and update META_TOKEN= in your .env file")
            print("\n  Also ensure your app has 'Ads Library API' enabled:")
            print("  https://developers.facebook.com/apps/<YOUR_APP_ID>/add/")
            return False

    # 3. Quick probe of the Ad Library endpoint itself
    probe = requests.get(
        AD_LIBRARY_URL,
        params={
            "access_token": META_TOKEN,
            "search_terms": "test",
            "ad_reached_countries": '["US"]',
            "ad_active_status": "ALL",
            "fields": "id",
            "limit": 1,
        },
    )
    if probe.status_code != 200:
        err = probe.json().get("error", {})
        subcode = err.get("error_subcode")
        msg = err.get("message", "")

        if subcode == 2332002:
            print("\n  APP PERMISSION ERROR: Your app hasn't been granted Ad Library API access.")
            print("  Even with 'ads_read', the app itself needs to have the")
            print("  'Ads Library API' product added in Meta for Developers.")
            print("\n  Steps to request access:")
            print("  1. Go to https://developers.facebook.com/apps/")
            print("  2. Open your app → Add Products → search 'Ads Library API'")
            print("  3. Complete Business Verification if prompted")
            print("  4. Once approved, regenerate your token and retry")
        else:
            print(f"\n  AD LIBRARY ERROR ({subcode}): {msg}")
        return False

    print("  Ad Library API access: OK")
    return True


# ---------------------------------------------------------------------------
# Fetch & parse
# ---------------------------------------------------------------------------

def fetch_ads_for_competitor(search_term: str) -> list[dict]:
    params = {
        "access_token": META_TOKEN,
        "search_terms": search_term,
        "ad_reached_countries": '["US"]',
        "ad_active_status": "ALL",
        "fields": ",".join([
            "id",
            "ad_creative_bodies",
            "ad_creative_link_captions",
            "ad_creative_link_descriptions",
            "ad_creative_link_titles",
            "ad_delivery_start_time",
            "ad_delivery_stop_time",
            "ad_snapshot_url",
            "bylines",
            "currency",
            "delivery_by_region",
            "demographic_distribution",
            "estimated_audience_size",
            "impressions",
            "page_name",
            "publisher_platforms",
            "spend",
            "languages",
        ]),
        "limit": 50,
    }

    ads = []
    url = AD_LIBRARY_URL

    while url:
        response = requests.get(url, params=params if url == AD_LIBRARY_URL else {})
        if response.status_code != 200:
            err = response.json().get("error", {})
            print(f"  ERROR {response.status_code} for '{search_term}': {err.get('message', response.text[:200])}")
            break

        data = response.json()
        page_ads = data.get("data", [])
        ads.extend(page_ads)

        next_page = data.get("paging", {}).get("next")
        url = next_page if next_page else None

        if next_page:
            time.sleep(0.5)

    return ads


def parse_ad(raw: dict, competitor: str) -> dict:
    start = raw.get("ad_delivery_start_time", "")
    stop = raw.get("ad_delivery_stop_time", "")

    days_running = None
    if start:
        try:
            start_dt = datetime.fromisoformat(start[:10])
            end_dt = datetime.fromisoformat(stop[:10]) if stop else datetime.today()
            days_running = (end_dt - start_dt).days
        except ValueError:
            pass

    bodies = raw.get("ad_creative_bodies") or []
    titles = raw.get("ad_creative_link_titles") or []
    captions = raw.get("ad_creative_link_captions") or []
    descriptions = raw.get("ad_creative_link_descriptions") or []
    impressions = raw.get("impressions", {})

    return {
        "competitor": competitor,
        "ad_id": raw.get("id"),
        "page_name": raw.get("page_name"),
        "ad_copy": bodies[0] if bodies else None,
        "headline": titles[0] if titles else None,
        "cta_caption": captions[0] if captions else None,
        "description": descriptions[0] if descriptions else None,
        "platforms": raw.get("publisher_platforms", []),
        "impression_lower": impressions.get("lower_bound"),
        "impression_upper": impressions.get("upper_bound"),
        "start_date": start[:10] if start else None,
        "stop_date": stop[:10] if stop else None,
        "days_running": days_running,
        "snapshot_url": raw.get("ad_snapshot_url"),
        "languages": raw.get("languages", []),
        "spend": raw.get("spend", {}),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not META_TOKEN:
        print("ERROR: META_TOKEN is not set in .env")
        return

    print("=" * 60)
    if not validate_token():
        print("\nAborting. Fix the token issues above and re-run.")
        return
    print("=" * 60)
    print()

    today = date.today().isoformat()
    output_file = f"ads_raw_{today}.json"

    all_results = {}
    total_ads = 0

    for competitor in COMPETITORS:
        print(f"Fetching ads for: {competitor} ...")
        raw_ads = fetch_ads_for_competitor(competitor)
        parsed = [parse_ad(ad, competitor) for ad in raw_ads]
        all_results[competitor] = parsed
        total_ads += len(parsed)
        print(f"  Found {len(parsed)} ads")
        time.sleep(1)

    output = {
        "fetched_date": today,
        "total_ads": total_ads,
        "competitors": all_results,
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone. {total_ads} total ads saved to {output_file}")


if __name__ == "__main__":
    main()
