import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote_plus

sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.browser import launch_browser, handle_consent, close_browser


def search_google_maps(page, vertical, city, state):
    query = f"{vertical} in {city}, {state}"
    search_url = "https://www.google.com/maps/search/" + query.replace(" ", "+")

    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=90000)
    except Exception:
        try:
            page.screenshot(path="logs/proxy_search_debug.png", timeout=5000)
        except Exception:
            pass
        return []

    handle_consent(page)

    try:
        page.wait_for_selector('div[role="feed"]', timeout=20000)
    except Exception:
        try:
            page.screenshot(path="logs/proxy_search_debug.png", timeout=5000)
        except Exception:
            pass
        return []

    # Scroll results panel to load all listings
    prev_count = 0
    for _ in range(15):
        count = page.locator('div[role="feed"] a[href*="/maps/place/"]').count()
        if count == prev_count and count > 0:
            break
        prev_count = count
        page.locator('div[role="feed"]').evaluate("el => el.scrollBy(0, 3000)")
        time.sleep(2)
        if page.locator("text=You've reached the end of the list").count() > 0:
            break

    if page.locator('div[role="feed"] a[href*="/maps/place/"]').count() == 0:
        try:
            page.screenshot(path="logs/proxy_search_debug.png", full_page=False)
        except Exception:
            pass

    results = []
    cards = page.locator('div[role="feed"] > div').all()

    for card in cards:
        try:
            link = card.locator('a[href*="/maps/place/"]').first
            if not link.count():
                continue
            maps_url = link.get_attribute("href")
            if not maps_url:
                continue

            all_text = card.inner_text()
            lines = [l.strip() for l in all_text.split('\n') if l.strip()]
            if not lines:
                continue

            # Skip "Sponsored" label — actual name is next line
            business_name = lines[0]
            if business_name.lower() == "sponsored" and len(lines) > 1:
                business_name = lines[1]

            # If name looks like a rating, icon, or garbage, extract from URL instead.
            # Maps URLs always contain the name: /maps/place/Business+Name/data=...
            if not business_name or len(business_name) < 3 or re.match(r'^[\d\W]+$', business_name):
                m_url = re.search(r'/maps/place/([^/@?]+)', maps_url)
                if m_url:
                    business_name = unquote_plus(m_url.group(1))

            # Extract rating + review count as a pair — Google always renders them
            # adjacent as "4.2 (234)", so matching together avoids capturing an
            # unrelated parenthetical number (suite, year, etc.) as the review count.
            star_rating = None
            total_reviews = None
            normalized = all_text.replace('\n', ' ')
            m = re.search(r'\b(\d\.\d)\b\s*\(([0-9,]+)\)', normalized)
            if m:
                star_rating = float(m.group(1))
                total_reviews = int(m.group(2).replace(',', ''))
            else:
                # Fallback: rating without a review count (e.g. brand-new listing)
                m = re.search(r'\b(\d\.\d)\b', normalized)
                if m:
                    star_rating = float(m.group(1))

            results.append({
                "business_name": business_name,
                "star_rating": star_rating,
                "total_reviews": total_reviews,
                "maps_url": maps_url,
            })
        except Exception:
            continue

    return results


def get_business_details(page, maps_url):
    page.goto(maps_url, wait_until="domcontentloaded", timeout=60000)

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

    return details


if __name__ == "__main__":
    Path("logs").mkdir(exist_ok=True)

    browser, page = launch_browser()

    print("Searching: plumber in Austin, TX")
    listings = search_google_maps(page, "plumber", "Austin", "TX")
    print(f"Total results found: {len(listings)}")

    qualified = [
        b for b in listings
        if b["star_rating"] is not None
        and b["total_reviews"] is not None
        and 3.0 <= b["star_rating"] <= 4.9
        and b["total_reviews"] >= 15
    ]
    print(f"Pass base filter (3.0-4.9 stars, 15+ reviews): {len(qualified)}")

    if qualified:
        first = qualified[0]
        print(f"\nGetting details for: {first['business_name']}")
        details = get_business_details(page, first["maps_url"])
        first.update(details)
        print(f"  Phone:   {details['phone']}")
        print(f"  Address: {details['address']}")
        print(f"  City:    {details['city']}, State: {details['state']}")

    close_browser(browser)

    output_path = Path("logs/stage4_results.json")
    with open(output_path, "w") as f:
        json.dump(listings, f, indent=2)
    print(f"\nSaved {len(listings)} results to {output_path}")
    print("Stage 4 passed")
