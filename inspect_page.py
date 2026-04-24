"""Dumps the rendered HTML of one Ad Library search to help debug selectors."""
from playwright.sync_api import sync_playwright

COMPETITOR = "StoryWorth"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-US",
    )
    page = context.new_page()

    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country=US"
        f"&q={COMPETITOR}&search_type=keyword_unordered&media_type=all"
    )
    print(f"Loading: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    # Dismiss cookie banners
    for selector in ['button:has-text("Allow all cookies")', 'button:has-text("Accept All")']:
        try:
            page.click(selector, timeout=2000)
        except Exception:
            pass

    page.wait_for_timeout(2000)

    # Save screenshot
    page.screenshot(path="inspect_screenshot.png", full_page=False)
    print("Screenshot saved: inspect_screenshot.png")

    # Save full HTML
    html = page.content()
    with open("inspect_page.html", "w") as f:
        f.write(html)
    print(f"HTML saved: inspect_page.html ({len(html):,} bytes)")

    # Print all unique link hrefs containing 'ads/library'
    links = page.eval_on_selector_all(
        'a[href*="ads/library"]',
        "els => els.map(e => e.href).filter((v, i, a) => a.indexOf(v) === i)"
    )
    print(f"\nAd Library links found ({len(links)}):")
    for l in links[:20]:
        print(f"  {l}")

    # Print visible text of the first 3000 chars
    body_text = page.inner_text("body")
    print(f"\n--- First 3000 chars of visible page text ---")
    print(body_text[:3000])

    browser.close()
