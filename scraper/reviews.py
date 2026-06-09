import json
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.browser import launch_browser, handle_consent, close_browser
from scraper.maps import search_google_maps


def _quick_extract(review_el):
    """Extract only stars, date, reply — no text expansion needed for signal checking."""
    review_stars = None
    stars_el = review_el.locator('[aria-label*="star"]').first
    if stars_el.count():
        m = re.search(r'(\d+)', stars_el.get_attribute("aria-label") or "")
        if m:
            review_stars = int(m.group(1))

    date_el = review_el.locator('span.rsqaWe, span[class*="xRkPPb"]').first
    review_date_raw = date_el.inner_text().strip() if date_el.count() else ""

    reply_el = review_el.locator('div.CDe7pd').first
    has_owner_reply = reply_el.count() > 0

    owner_reply_date_raw = None
    if has_owner_reply:
        reply_date_el = reply_el.locator('span.DZSIDd, span[class*="xRkPPb"]').first
        if reply_date_el.count():
            owner_reply_date_raw = reply_date_el.inner_text().strip()

    return {
        "reviewer_name": "Unknown",
        "review_stars": review_stars,
        "review_date_raw": review_date_raw,
        "review_text": "",
        "has_owner_reply": has_owner_reply,
        "owner_reply_date_raw": owner_reply_date_raw,
    }


def _extract_review_el(review_el):
    name_el = review_el.locator('a[href*="maps/contrib"]').first
    if not name_el.count():
        name_el = review_el.locator('div.d4r55').first
    reviewer_name = name_el.inner_text().strip() if name_el.count() else "Unknown"

    review_stars = None
    stars_el = review_el.locator('[aria-label*="star"]').first
    if stars_el.count():
        aria = stars_el.get_attribute("aria-label") or ""
        m = re.search(r'(\d+)', aria)
        if m:
            review_stars = int(m.group(1))

    date_el = review_el.locator('span.rsqaWe, span[class*="xRkPPb"]').first
    review_date_raw = date_el.inner_text().strip() if date_el.count() else ""

    text_el = review_el.locator('span.wiI7pd, span[class*="MyEned"]').first
    review_text = text_el.inner_text().strip() if text_el.count() else ""

    reply_el = review_el.locator('div.CDe7pd').first
    has_owner_reply = reply_el.count() > 0

    owner_reply_date_raw = None
    if has_owner_reply:
        reply_date_el = reply_el.locator('span.DZSIDd, span[class*="xRkPPb"]').first
        if reply_date_el.count():
            owner_reply_date_raw = reply_date_el.inner_text().strip()

    return {
        "reviewer_name": reviewer_name,
        "review_stars": review_stars,
        "review_date_raw": review_date_raw,
        "review_text": review_text,
        "has_owner_reply": has_owner_reply,
        "owner_reply_date_raw": owner_reply_date_raw,
    }


def _click_reviews_tab_and_sort(page):
    """Click the Reviews tab and sort by Newest. Called after page is loaded."""
    try:
        tab = page.locator('button[role="tab"]:has-text("Reviews")').first
        tab.wait_for(timeout=10000)
        tab.click()
        time.sleep(2)
    except Exception:
        pass

    try:
        sort_btn = page.locator('button[aria-label*="Sort"]').first
        sort_btn.wait_for(timeout=5000)
        sort_btn.click()
        time.sleep(1)
        page.locator('div[role="menuitemradio"]:has-text("Newest"), li[role="menuitemradio"]:has-text("Newest")').first.click()
        time.sleep(2)
    except Exception:
        pass


def _collect_reviews(page, max_reviews=50, stop_check=None):
    """
    Assumes page is already on the sorted Reviews tab.
    Phase 1: scroll + quick_extract with optional early stop.
    Phase 2: full extraction with More-button expansion.
    Returns raw review list.
    """
    # Sorting reloads the list asynchronously — wait for the first card before
    # starting the scroll loop or count=0 → count==prev immediately breaks.
    try:
        page.wait_for_selector('div[data-review-id]', timeout=10000)
    except Exception:
        return []

    quick_buffer = []
    early_stop_at = None

    for _ in range(20):
        current_count = page.locator('div[data-review-id]').count()

        if stop_check and current_count > len(quick_buffer):
            for el in page.locator('div[data-review-id]').all()[len(quick_buffer):current_count]:
                try:
                    quick_buffer.append(_quick_extract(el))
                except Exception:
                    continue
            if quick_buffer and stop_check(quick_buffer):
                early_stop_at = len(quick_buffer)
                break

        if current_count >= max_reviews:
            break

        prev = current_count
        page.locator('div[role="main"]').evaluate("el => el.scrollBy(0, 3000)")
        time.sleep(1.5)
        if page.locator('div[data-review-id]').count() == prev:
            break

    extract_limit = early_stop_at or min(
        page.locator('div[data-review-id]').count(), max_reviews
    )

    try:
        for btn in page.locator('button.w8nwRe').all()[:extract_limit]:
            try:
                btn.click()
                time.sleep(0.2)
            except Exception:
                pass
    except Exception:
        pass

    results = []
    for el in page.locator('div[data-review-id]').all()[:extract_limit]:
        try:
            results.append(_extract_review_el(el))
        except Exception:
            continue

    return results


def scrape_reviews(page, maps_url, max_reviews=50, stop_check=None):
    page.goto(maps_url, wait_until="domcontentloaded", timeout=60000)
    handle_consent(page)
    time.sleep(2)
    _click_reviews_tab_and_sort(page)
    return _collect_reviews(page, max_reviews, stop_check)


def get_details_and_reviews(page, maps_url, max_reviews=50, stop_check=None):
    """
    Single-navigation replacement for calling get_business_details() then
    scrape_reviews() separately. Saves one full proxy page load per business.
    Returns (details_dict, raw_reviews_list).
    """
    page.goto(maps_url, wait_until="domcontentloaded", timeout=60000)
    handle_consent(page)
    time.sleep(2)

    details = {"address": None, "city": None, "state": None, "phone": None, "website": None}
    try:
        page.wait_for_selector('div[role="main"]', timeout=15000)

        phone_el = page.locator('[data-item-id^="phone:tel:"]').first
        if phone_el.count():
            raw = phone_el.get_attribute("data-item-id") or ""
            details["phone"] = raw.replace("phone:tel:", "")

        addr_el = page.locator('[data-item-id="address"]').first
        if addr_el.count():
            full_address = addr_el.inner_text().strip()
            details["address"] = full_address
            parts = [p.strip() for p in full_address.split(",")]
            if parts and parts[-1].strip() in ("United States", "USA", "US"):
                parts = parts[:-1]
            if len(parts) >= 2:
                details["city"] = parts[-2].strip()
                state_zip = parts[-1].strip().split()
                if state_zip:
                    details["state"] = state_zip[0]

        website_el = page.locator('a[data-item-id="authority"]').first
        if website_el.count():
            details["website"] = website_el.get_attribute("href")
    except Exception:
        pass

    _click_reviews_tab_and_sort(page)
    reviews = _collect_reviews(page, max_reviews, stop_check)
    return details, reviews


def convert_relative_date(date_text):
    today = date.today()
    if not date_text:
        return None
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

    # Google shows absolute dates for older reviews e.g. "Jun 15, 2025" or "June 15, 2025"
    from datetime import datetime as _dt
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"):
        try:
            return _dt.strptime(date_text.strip(), fmt).date()
        except ValueError:
            continue

    return None


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
