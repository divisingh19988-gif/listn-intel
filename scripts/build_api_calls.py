import os
import sys
import time
import requests

ENDPOINTS = [
    "https://graph.facebook.com/v25.0/me",
    "https://graph.facebook.com/v25.0/me/adaccounts",
]

TARGET_CALLS = 500
SLEEP_SECONDS = 2


def main() -> int:
    token = os.environ.get("META_TOKEN")
    if not token:
        print("META_TOKEN environment variable is not set.", file=sys.stderr)
        return 1

    successful = 0
    failed = 0
    total = 0

    while total < TARGET_CALLS:
        endpoint = ENDPOINTS[total % len(ENDPOINTS)]
        total += 1

        params = {
            "fields": "id,name",
            "access_token": token,
        }

        try:
            resp = requests.get(endpoint, params=params, timeout=30)
            status = resp.status_code
            if status == 200:
                successful += 1
            else:
                failed += 1
                try:
                    err = resp.json().get("error", {})
                    if err.get("code") == 190:
                        print(f"Call {total}/{TARGET_CALLS} — {endpoint} — {status} (invalid token, stopping)")
                        print(f"\nFinal summary: total={total} successful={successful} failed={failed}")
                        return 1
                except ValueError:
                    pass
        except requests.RequestException as e:
            status = f"ERR({e.__class__.__name__})"
            failed += 1

        if total % 25 == 0:
            print(f"Call {total}/{TARGET_CALLS} — {endpoint} — {status}")

        if total < TARGET_CALLS:
            time.sleep(SLEEP_SECONDS)

    print(f"\nFinal summary: total={total} successful={successful} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
