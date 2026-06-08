# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Altrium Media lead scraper — searches Google Maps for businesses across 166 verticals (8 categories per v3 PDF) and 4,117 US cities, qualifies them against 5 review-based signals, and outputs leads to Supabase + Excel. The scraper uses Playwright with residential proxies (Decodo) to avoid detection.

## Environment Setup

Always activate the virtual environment before running anything:
```bash
source venv/bin/activate
```

All scripts must be run from the project root (`/Users/Macbook/Documents/Github/maps_scraper/`).

## Running the Scraper

**Demo / test run (one search, proxy on):**
```bash
python3 main.py
# TEST_MODE = True in main.py — runs "plumber in Houston, TX"
```

**Full production run (all cities × all verticals, proxy on):**
```bash
# Set TEST_MODE = False in main.py first
python3 main.py
```

**Run individual stage scripts for debugging:**
```bash
python3 scraper/browser.py     # proxy IP check
python3 scraper/maps.py        # search + scrape listings
python3 scraper/reviews.py     # review scraping
python3 signals/qualify.py     # signal logic against stage5_reviews.json
python3 output/database.py     # Supabase insert + deduplication test
python3 enrichment/email.py    # email/phone scraping from websites
python3 config/verticals.py    # verify vertical count
python3 config/cities.py       # verify cities loaded from CSV
```

## Architecture

The pipeline flows in one direction — `main.py` orchestrates everything:

```
search_google_maps()        → list of business listings (name, rating, reviews, maps_url)
get_business_details()      → adds phone, address, city, state, website URL
scrape_reviews()            → up to 50 reviews sorted by Newest
process_reviews()           → converts relative dates ("3 weeks ago") to ISO dates
qualify_business()          → checks 5 signals, returns signal dict or None
enrich_business_email()     → scrapes website for all emails + phones
insert_lead()               → upserts to Supabase, deduplicates by phone
export_to_excel()           → writes logs/leads.xlsx
```

**Loop order in production:** city-outer, vertical-inner. Completes all 60 verticals in one city before moving to the next. Checkpoint saves to `logs/checkpoint.json` after every search so interrupted runs resume correctly.

## Key Design Decisions

**Browser:** `launch_browser()` with no argument reads `USE_PROXY` from `.env` (default `false`). Pass `use_proxy=True` explicitly in production paths. For VPS deployment, set `HEADLESS=true` in `.env`.

**Proxy:** Decodo residential proxies via `us.decodo.com:10000` (US country endpoint, rotating port). Username must use Decodo's documented format: `user-[username]-country-us`. Port `10000` is the rotating port; `10001–29999` are sticky ports (not used here). The `USE_PROXY` env var controls proxy on/off — standalone debug scripts (`maps.py`, `reviews.py`) also respect this env var now. The `handle_consent()` function dismisses Google's GDPR consent dialog which can appear with some proxy IPs.

**Email prioritisation:** Emails are scored — `john.smith@` (score 4) beats `jsmith@` (score 3) beats `info@` (score 1). `enrich_business_email()` returns all found emails and phones as comma-separated strings in `all_emails` / `all_phones`, with the best email in `business_email`.

**Deduplication:** Enforced at the database level via a unique index on `phone`. The upsert uses `ignore_duplicates=True` so duplicate phones are silently skipped without errors.

**Signal priority:** Signals are checked A → B → C → D → E and the first match wins. Signal E was updated from the original GUIDE.md spec per the PDF requirements — it fires when 3+ positive replies exist in 90 days AND any unanswered negative reviews exist (not "zero negative replied in 90 days").

## Credentials (.env)

```
DECODO_HOST / DECODO_PORT / DECODO_USER / DECODO_PASS   — Decodo proxy
SUPABASE_URL / SUPABASE_KEY                              — Supabase project
```

## Supabase Schema

The `leads` table has these columns beyond the standard 15 output fields:
- `all_emails` text — all emails found on website, named contacts first
- `all_phones` text — all phones found on website
- `review_snippet` text — bad review trimmed to 200 chars at word boundary, for email templates

## Config Files

- `config/verticals.py` — 166 verticals across 8 categories (v3 PDF): Home Services & Heavy Industrial, Healthcare, Legal & Investigative, Financial, Automotive/Marine/Aviation, B2B/Commercial/Real Estate, Education, Luxury Lifestyle
- `config/cities.py` — reads `uscities.csv` (simplemaps.com), filters to 10k+ population, sorts by population descending. `get_cities_by_state("TX")` and `get_top_cities(n)` are available helpers.

## Output Files

All output lands in `logs/` (gitignored):
- `scraper.log` — full run log
- `leads.xlsx` — Excel export of inserted leads
- `checkpoint.json` — resume position for interrupted full runs
- `test_run.json` — summary JSON from TEST_MODE runs
