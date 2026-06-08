import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.browser import launch_browser, handle_consent, close_browser
from scraper.maps import search_google_maps


def scrape_reviews(page, maps_url, max_reviews=50):
    page.goto(maps_url, wait_until="domcontentloaded", timeout=60000)
    handle_consent(page)
    time.sleep(2)

    # Click the Reviews tab
    try:
        tab = page.locator('button[role="tab"]:has-text("Reviews")').first
        tab.wait_for(timeout=10000)
        tab.click()
        time.sleep(2)
    except Exception:
        pass

    # Sort by Newest
    try:
        sort_btn = page.locator('button[aria-label*="Sort"]').first
        sort_btn.wait_for(timeout=5000)
        sort_btn.click()
        time.sleep(1)
        page.locator('div[role="menuitemradio"]:has-text("Newest"), li[role="menuitemradio"]:has-text("Newest")').first.click()
        time.sleep(2)
    except Exception:
        pass

    # Scroll to load up to max_reviews
    for _ in range(20):
        count = page.locator('div[data-review-id]').count()
        if count >= max_reviews:
            break
        page.locator('div[role="main"]').evaluate("el => el.scrollBy(0, 3000)")
        time.sleep(1.5)
        if page.locator('div[data-review-id]').count() == count:
            break

    # Expand truncated review text
    try:
        for btn in page.locator('button.w8nwRe').all()[:max_reviews]:
            try:
                btn.click()
                time.sleep(0.2)
            except Exception:
                pass
    except Exception:
        pass

    results = []
    for review_el in page.locator('div[data-review-id]').all()[:max_reviews]:
        try:
            # Reviewer name
            name_el = review_el.locator('a[href*="maps/contrib"]').first
            if not name_el.count():
                name_el = review_el.locator('div.d4r55').first
            reviewer_name = name_el.inner_text().strip() if name_el.count() else "Unknown"

            # Star rating from aria-label
            review_stars = None
            stars_el = review_el.locator('[aria-label*="star"]').first
            if stars_el.count():
                aria = stars_el.get_attribute("aria-label") or ""
                m = re.search(r'(\d+)', aria)
                if m:
                    review_stars = int(m.group(1))

            # Review date
            date_el = review_el.locator('span.rsqaWe, span[class*="xRkPPb"]').first
            review_date_raw = date_el.inner_text().strip() if date_el.count() else ""

            # Review text
            text_el = review_el.locator('span.wiI7pd, span[class*="MyEned"]').first
            review_text = text_el.inner_text().strip() if text_el.count() else ""

            # Owner reply
            reply_el = review_el.locator('div.CDe7pd').first
            has_owner_reply = reply_el.count() > 0

            owner_reply_date_raw = None
            if has_owner_reply:
                reply_date_el = reply_el.locator('span.DZSIDd, span[class*="xRkPPb"]').first
                if reply_date_el.count():
                    owner_reply_date_raw = reply_date_el.inner_text().strip()

            results.append({
                "reviewer_name": reviewer_name,
                "review_stars": review_stars,
                "review_date_raw": review_date_raw,
                "review_text": review_text,
                "has_owner_reply": has_owner_reply,
                "owner_reply_date_raw": owner_reply_date_raw,
            })
        except Exception:
            continue

    return results


def convert_relative_date(date_text):
    today = date.today()
    if not date_text:
        return today
    text = date_text.lower().strip()

    if re.search(r'hour|minute|just now', text):
        return today
    m = re.search(r'(\d+)\s+day', text)
    if m:
        return today - timedelta(days=int(m.group(1)))
    if re.search(r'a\s+week|1\s+week', text):
        return today - timedelta(days=7)
    m = re.search(r'(\d+)\s+week', text)
    if m:
        return today - timedelta(days=int(m.group(1)) * 7)
    if re.search(r'a\s+month|1\s+month', text):
        return today - timedelta(days=30)
    m = re.search(r'(\d+)\s+month', text)
    if m:
        return today - timedelta(days=int(m.group(1)) * 30)
    if re.search(r'a\s+year|1\s+year', text):
        return today - timedelta(days=365)
    m = re.search(r'(\d+)\s+year', text)
    if m:
        return today - timedelta(days=int(m.group(1)) * 365)

    return today


def process_reviews(raw_reviews):
    for review in raw_reviews:
        d = convert_relative_date(review.get("review_date_raw", ""))
        review["review_date"] = d.isoformat() if d else None
        owner_raw = review.get("owner_reply_date_raw")
        d2 = convert_relative_date(owner_raw) if owner_raw else None
        review["owner_reply_date"] = d2.isoformat() if d2 else None
    return raw_reviews


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)

    browser, page = launch_browser()

    listings = search_google_maps(page, "plumber", "Austin", "TX")

    target = next((b for b in listings if b.get("total_reviews") and b["total_reviews"] > 0), None)
    if not target:
        print("No business with reviews found")
        close_browser(browser)
        exit(1)

    print(f"Scraping reviews for: {target['business_name']} ({target['total_reviews']} reviews)")
    raw = scrape_reviews(page, target["maps_url"])
    print(f"Reviews scraped: {len(raw)}")

    reviews = process_reviews(raw)

    print("\nSample reviews:")
    for r in reviews[:5]:
        stars = "★" * (r["review_stars"] or 0)
        print(f"  {stars} | {r['review_date']} | reply={r['has_owner_reply']} | {r['review_text'][:80]}")

    close_browser(browser)

    output_path = Path("logs/stage5_reviews.json")
    with open(output_path, "w") as f:
        json.dump(reviews, f, indent=2, default=str)
    print(f"\nSaved {len(reviews)} reviews to {output_path}")
    print("Stage 5 passed")
