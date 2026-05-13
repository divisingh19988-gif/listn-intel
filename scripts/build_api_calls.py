import os
import sys
import time
import requests

SEARCH_TERMS = [
    "remento", "storyworth", "meminto", "storykeeper",
    "memory app", "life stories", "voice memories",
    "family stories", "grandparent gift", "hereafter",
    "keepsake", "legacy app", "record stories",
    "preserve memories", "senior companion app",
]

TARGET_CALLS = 500
SLEEP_SECONDS = 2
ENDPOINT = "https://graph.facebook.com/v19.0/ads_archive"


def main() -> int:
    token = os.environ.get("META_TOKEN")
    if not token:
        print("META_TOKEN environment variable is not set.", file=sys.stderr)
        return 1

    successful = 0
    failed = 0
    total = 0
    i = 0

    while total < TARGET_CALLS:
        term = SEARCH_TERMS[i % len(SEARCH_TERMS)]
        i += 1
        total += 1

        params = {
            "search_terms": term,
            "ad_reached_countries": '["US"]',
            "ad_type": "ALL",
            "limit": 10,
            "fields": "id,page_name",
            "access_token": token,
        }

        try:
            resp = requests.get(ENDPOINT, params=params, timeout=30)
            status = resp.status_code
            if status == 200:
                successful += 1
            else:
                failed += 1
                try:
                    err = resp.json().get("error", {})
                    if err.get("code") == 190:
                        print(f"Call {total}/{TARGET_CALLS} — {term} — {status} (invalid token, stopping)")
                        print(f"\nFinal summary: total={total} successful={successful} failed={failed}")
                        return 1
                except ValueError:
                    pass
        except requests.RequestException as e:
            status = f"ERR({e.__class__.__name__})"
            failed += 1

        if total % 25 == 0:
            print(f"Call {total}/{TARGET_CALLS} — {term} — {status}")

        if total < TARGET_CALLS:
            time.sleep(SLEEP_SECONDS)

    print(f"\nFinal summary: total={total} successful={successful} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
