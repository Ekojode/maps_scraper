# Altrium Lead Scraper — Claude Code Build Guide

## What We Are Building

A fully automated Google Maps business scraper that:
- Searches all 57 Altrium verticals across every US city
- Uses Playwright + Decodo residential proxies (no paid APIs)
- Qualifies businesses against 5 specific signals
- Outputs clean leads to Supabase with all 15 required fields
- Runs on Mac locally, later deployable to a VPS

**Everything is built and tested one stage at a time. Do not skip ahead.**

---

## Tech Stack

| Tool | Purpose | Cost |
|---|---|---|
| Python 3.10+ | Core language | Free |
| Playwright | Browser automation | Free |
| playwright-stealth | Anti-bot detection patches | Free |
| Decodo proxies | Residential IP rotation | $35/mo |
| Supabase | Lead database output | Free tier |
| python-dotenv | Manage credentials securely | Free |
| httpx | HTTP requests for email enrichment | Free |
| tenacity | Retry logic on failures | Free |

---

## Project Structure

All code lives in: `/Users/Macbook/Documents/Github/maps_scraper/`

```
maps_scraper/             ← project root (this folder)
├── .env                  # All credentials (never commit this)
├── .gitignore
├── requirements.txt
├── config/
│   ├── verticals.py      # All 57 Altrium verticals
│   └── cities.py         # US cities list
├── scraper/
│   ├── browser.py        # Playwright + proxy + stealth setup
│   ├── maps.py           # Google Maps search and business scraping
│   └── reviews.py        # Review scraping and date conversion
├── signals/
│   └── qualify.py        # All 5 Altrium qualification signals
├── output/
│   ├── schema.sql        # Supabase table definition
│   └── database.py       # Supabase write logic
├── enrichment/
│   └── email.py          # Email scraping from business website
├── logs/
│   └── scraper.log       # Auto-generated run logs
└── main.py               # Entry point — runs the full pipeline
```

---

## Credentials Needed

Create a `.env` file in the project root with these values:

```env
# Decodo Residential Proxies
# Sign up at: https://decodo.com
# Format: gate.decodo.com:10001
DECODO_HOST=gate.decodo.com
DECODO_PORT=10001
DECODO_USER=your_decodo_username
DECODO_PASS=your_decodo_password

# Supabase
# Get these from: supabase.com → your project → Settings → API
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_anon_public_key
```

---

## Supabase Table Schema

Run this SQL in the Supabase SQL editor before starting Stage 6:

```sql
CREATE TABLE leads (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  business_name text NOT NULL,
  phone text UNIQUE NOT NULL,          -- deduplicated by phone
  business_email text,
  city text,
  state text,
  vertical text,
  qualifying_signal text,              -- a, b, c, d, or e
  star_rating numeric(2,1),
  total_reviews integer,
  bad_review_date date,
  bad_review_stars integer,
  bad_review_text text,
  bad_review_author text,
  days_since_last_response integer,
  maps_url text,
  scraped_at timestamptz DEFAULT now()
);

-- Enforce phone deduplication at database level
CREATE UNIQUE INDEX leads_phone_idx ON leads (phone);
```

---

## The 57 Altrium Verticals

### Home Services (26)
```
plumber, roofer, HVAC contractor, electrician, tree service,
pest control, concrete contractor, water damage restoration,
pool service, garage door company, moving company,
landscaping company, fence company, tile contractor,
flooring company, painting contractor, general contractor,
home remodeling company, bathroom remodeling company,
kitchen remodeling company, window replacement company,
siding contractor, gutter company, demolition company,
asphalt paving company, welding service
```

### Healthcare (12)
```
dentist, orthodontist, oral surgeon, chiropractor, med spa,
plastic surgeon, cosmetic dentist, dermatologist,
physical therapist, family doctor, urgent care, podiatrist
```

### Legal (13)
```
car accident lawyer, personal injury lawyer, family lawyer,
divorce lawyer, criminal defense lawyer, estate planning lawyer,
immigration lawyer, real estate lawyer, business lawyer,
tax attorney, bankruptcy lawyer, civil litigation lawyer,
employment lawyer
```

### Financial (8)
```
financial advisor, insurance agent, mortgage broker,
tax accountant, CPA, bookkeeper, wealth management,
retirement planning
```

---

## The 5 Qualification Signals

Every business must pass the base filters first:
- ✅ Star rating between 3.0 and 4.9
- ✅ Total reviews 15 or more

Then at least ONE of these signals must fire:

| Signal | Description |
|---|---|
| **a** | 1–3 star review in last 60 days with NO owner response |
| **b** | 1–3 star review in 61–90 day window with NO owner response |
| **c** | 3 or more unanswered reviews in last 60 days (any star rating) |
| **d** | Owner's last response to ANY review was 45+ days ago |
| **e** | Owner responded to 3+ positive reviews but ZERO negative reviews in last 90 days |

---

## The 15 Output Fields

| Field | Description |
|---|---|
| `business_name` | Full name as listed on Google Maps |
| `phone` | Primary phone in E.164 format (+12125551234) |
| `business_email` | From profile or scraped from website |
| `city` | City from business profile |
| `state` | Two-letter US state abbreviation |
| `vertical` | Exact search vertical that returned this business |
| `qualifying_signal` | Which signal fired: a, b, c, d, or e |
| `star_rating` | Overall rating e.g. 4.2 |
| `total_reviews` | Total review count |
| `bad_review_date` | Date of triggering review (ISO format YYYY-MM-DD) |
| `bad_review_stars` | Star rating of that review (1, 2, or 3) |
| `bad_review_text` | Full text of the triggering review |
| `bad_review_author` | Reviewer's display name |
| `days_since_last_response` | Integer days since owner last responded to any review |
| `maps_url` | Direct URL to Google Maps profile |

---

## Build Stages

Build and test each stage completely before moving to the next.
**Never skip a stage.**

---

### Stage 1 — Environment Setup

**Goal:** Python environment ready, all dependencies installed, Playwright browser downloaded.

**Instructions for Claude Code:**
```
Set up the Python environment for the Altrium scraper project on Mac:

1. Check Python version is 3.10 or higher. If not, tell me to install it from python.org
2. Work inside /Users/Macbook/Documents/Github/maps_scraper/ (the current project root — do NOT create a new folder)
3. Create a Python virtual environment: python3 -m venv venv
4. Activate it: source venv/bin/activate
5. Create requirements.txt with these packages:
   playwright
   playwright-stealth
   python-dotenv
   supabase
   httpx
   tenacity
   phonenumbers
6. Install them: pip install -r requirements.txt
7. Install Playwright's Chromium browser: playwright install chromium
8. Create the full folder structure:
   config/, scraper/, signals/, output/, enrichment/, logs/
9. Create a .gitignore that ignores: .env, venv/, logs/, __pycache__/, *.pyc
10. Create the .env file with placeholder credentials as shown in the guide
11. Confirm all installs succeeded and show me versions of Python and Playwright
```

**What success looks like:**
- No errors during pip install
- `playwright install chromium` completes without errors
- Python 3.10+ confirmed
- All folders created

---

### Stage 2 — Stealth Browser Launch (No Proxy)

**Goal:** Open a real Chromium browser with stealth patches. Confirm Google Maps loads without a CAPTCHA or block.

**Instructions for Claude Code:**
```
Create scraper/browser.py for the Altrium scraper.

This file must:
1. Import Playwright sync API and playwright_stealth
2. Define a function called launch_browser(use_proxy=False) that:
   - Launches Chromium in non-headless mode (so we can see it) for now
   - Applies playwright_stealth to the browser context
   - Sets viewport to 1280x800
   - Sets locale to en-US
   - Sets user agent to a realistic Chrome on Mac string
   - If use_proxy is True, reads DECODO_HOST, DECODO_PORT, DECODO_USER, 
     DECODO_PASS from .env and adds proxy settings
   - Returns the page object
3. Define a function called close_browser(browser) that closes cleanly
4. Add a __main__ block that:
   - Calls launch_browser()
   - Navigates to https://maps.google.com
   - Waits 5 seconds
   - Takes a screenshot saved to logs/stage2_test.png
   - Closes the browser
   - Prints "Stage 2 passed" if screenshot exists

Run it and show me the screenshot result.
```

**What success looks like:**
- Browser opens visually
- Google Maps loads (not a CAPTCHA page)
- Screenshot saved to logs/stage2_test.png
- No `navigator.webdriver` detection

---

### Stage 3 — Proxy Integration

**Goal:** Route all browser traffic through Decodo residential proxies. Confirm IP is not our real IP.

**Note:** You need real Decodo credentials in .env for this stage. If you don't have them yet, skip to Stage 4 and come back.

**Instructions for Claude Code:**
```
Test proxy integration in scraper/browser.py:

1. Update launch_browser() to accept use_proxy=True by default
2. Add a function called check_ip(page) that:
   - Navigates to https://api.ipify.org?format=json
   - Returns the IP address shown
3. Update the __main__ block to:
   - Launch browser WITH proxy (use_proxy=True)
   - Call check_ip() and print the result
   - Also print our real machine IP using a subprocess call to curl ifconfig.me
   - Compare the two — they must be DIFFERENT
   - Navigate to https://maps.google.com
   - Take a screenshot to logs/stage3_proxy_test.png
   - Print "Stage 3 passed — proxy working" if IPs differ

Load credentials from .env using python-dotenv.
Run it and show me the output.
```

**What success looks like:**
- Two different IPs printed
- Google Maps loads through the proxy
- No connection errors

---

### Stage 4 — Google Maps Search + Business Listing Scrape

**Goal:** Search one vertical in one city. Scrape all business listings from the results — name, rating, review count, address, phone, maps URL.

**Instructions for Claude Code:**
```
Create scraper/maps.py for the Altrium scraper.

This file must:
1. Import browser.py functions
2. Define search_google_maps(page, vertical, city, state) that:
   - Navigates to Google Maps
   - Types "{vertical} in {city}, {state}" into the search bar
   - Presses Enter and waits for results to load
   - Scrolls the results panel to load all listings (scroll until no new results appear)
   - Scrapes each business card in the results for:
     * business_name
     * star_rating (float)
     * total_reviews (integer, strip commas)
     * maps_url (the href of the listing)
   - Returns a list of dicts
3. Define get_business_details(page, maps_url) that:
   - Opens the business profile page
   - Scrapes: address, city, state, phone (raw format)
   - Returns a dict
4. Add a __main__ block that:
   - Searches for "plumber in Austin, TX"
   - Prints how many results were found
   - Filters to only businesses with rating between 3.0 and 4.9 AND 15+ reviews
   - Prints how many pass the filter
   - For the first passing business, calls get_business_details()
   - Saves all results to logs/stage4_results.json
   - Prints "Stage 4 passed"

Use explicit waits and selectors. Handle cases where rating or review count is missing.
Run it and show me the output.
```

**What success looks like:**
- At least 10 business results returned
- Rating and review count correctly parsed as numbers
- At least 1 business passes the filter
- Business detail page opens and scrapes correctly

---

### Stage 5 — Review Scraping

**Goal:** Click into a business profile, open the Reviews tab, sort by Newest, scroll to load 50 reviews, and scrape each review's full data.

**Instructions for Claude Code:**
```
Create scraper/reviews.py for the Altrium scraper.

This file must:
1. Define scrape_reviews(page, maps_url, max_reviews=50) that:
   - Navigates to the business Maps URL
   - Clicks the Reviews tab/button
   - Clicks the Sort button and selects "Newest"
   - Scrolls the review panel to load up to max_reviews reviews
   - For each review scrapes:
     * reviewer_name
     * review_stars (integer 1-5)
     * review_date_raw (the text shown e.g. "3 weeks ago")
     * review_text (full text, expand "More" button if present)
     * has_owner_reply (boolean — True if owner responded)
     * owner_reply_date_raw (text of owner reply date if exists, else None)
   - Returns a list of dicts, one per review

2. Define convert_relative_date(date_text) that converts relative date strings
   to real Python date objects using today's date:
   - "X hours ago" → today
   - "X days ago" → today minus X days
   - "a week ago" / "1 week ago" → today minus 7 days
   - "X weeks ago" → today minus X*7 days
   - "a month ago" / "1 month ago" → today minus 30 days
   - "X months ago" → today minus X*30 days
   - "a year ago" / "1 year ago" → today minus 365 days
   - "X years ago" → today minus X*365 days
   - Returns a datetime.date object

3. Define process_reviews(raw_reviews) that:
   - Runs convert_relative_date on review_date_raw and owner_reply_date_raw
   - Adds review_date (date object) and owner_reply_date (date object or None)
   - Returns the enriched list

4. Add a __main__ block that:
   - Opens this Maps URL: https://www.google.com/maps/search/plumber+in+Austin+TX
   - Takes the first business that has reviews
   - Runs scrape_reviews() on it
   - Runs process_reviews() on the result
   - Prints each review: stars, date, has_owner_reply, first 100 chars of text
   - Saves to logs/stage5_reviews.json
   - Prints "Stage 5 passed"

Handle edge cases: reviews with no text, reviews with no owner reply section.
Run it and show me the output.
```

**What success looks like:**
- 20+ reviews scraped from one business
- Dates correctly converted (e.g. "3 weeks ago" → a real date ~21 days ago)
- has_owner_reply correctly True/False
- No crashes on reviews with missing fields

---

### Stage 6 — All 5 Qualification Signals

**Goal:** Run the full Altrium signal logic against a list of processed reviews. Return which signal fired and the triggering review data.

**Instructions for Claude Code:**
```
Create signals/qualify.py for the Altrium scraper.

This file must:
1. Import datetime
2. Define qualify_business(reviews, business) that:
   - Takes a list of processed reviews (from Stage 5) and a business dict
   - Checks base filters first:
     * star_rating must be between 3.0 and 4.9 inclusive
     * total_reviews must be 15 or more
     * If either fails, return None immediately
   - Then checks each signal in order a → b → c → d → e
   - Returns a dict with:
     * qualifying_signal: "a", "b", "c", "d", or "e"
     * bad_review_date: ISO date string of triggering review
     * bad_review_stars: star rating of triggering review
     * bad_review_text: full text of triggering review
     * bad_review_author: reviewer name
     * days_since_last_response: integer
   - Returns None if no signal fires

3. The signal logic must be exactly:

   SIGNAL A:
   - Find any review where:
     * review_date is within last 60 days (from today)
     * review_stars is 1, 2, or 3
     * has_owner_reply is False
   - If found → return signal "a" with that review's data

   SIGNAL B:
   - Find any review where:
     * review_date is between 61 and 90 days ago
     * review_stars is 1, 2, or 3
     * has_owner_reply is False
   - If found → return signal "b" with that review's data

   SIGNAL C:
   - Count reviews in last 60 days where has_owner_reply is False (any star rating)
   - If count is 3 or more → return signal "c"
   - Use the oldest of those unanswered reviews as the bad_review data

   SIGNAL D:
   - Find the most recent review that has_owner_reply True
   - Calculate how many days ago owner_reply_date was
   - If 45 or more days → return signal "d"
   - bad_review_date = that review's date, days_since_last_response = that count

   SIGNAL E:
   - In the last 90 days:
     * Count reviews with has_owner_reply True AND review_stars 4 or 5 (positive)
     * Count reviews with has_owner_reply True AND review_stars 1, 2, or 3 (negative)
   - If positive_replied >= 3 AND negative_replied == 0 → return signal "e"
   - Use the most recent unanswered negative review as bad_review data

4. Define format_phone_e164(raw_phone, default_country="US") that:
   - Uses the phonenumbers library
   - Returns E.164 format e.g. +12125551234
   - Returns raw_phone unchanged if parsing fails

5. Add a __main__ block that:
   - Loads logs/stage5_reviews.json
   - Creates a mock business dict with rating 4.1 and total_reviews 47
   - Runs qualify_business()
   - Prints which signal fired and why
   - Prints "Stage 6 passed"

Run it and show me the output.
```

**What success looks like:**
- At least one signal fires on the test data
- Correct signal letter returned
- Triggering review data correctly captured
- Phone formatter correctly produces E.164 format

---

### Stage 7 — Supabase Output

**Goal:** Connect to Supabase and insert a qualified lead. Handle the unique phone constraint (upsert, not insert) so duplicates are rejected silently.

**Instructions for Claude Code:**
```
Create output/database.py for the Altrium scraper.

Before running this stage, make sure you have run the schema SQL from the guide
in your Supabase SQL editor to create the leads table.

This file must:
1. Load SUPABASE_URL and SUPABASE_KEY from .env
2. Define get_supabase_client() that returns an authenticated Supabase client
3. Define insert_lead(lead_dict) that:
   - Takes a dict with all 15 output fields
   - Uses upsert with on_conflict="phone" so duplicate phones are silently ignored
   - Returns True if inserted, False if duplicate/skipped
   - Logs the result either way
4. Define insert_leads_batch(leads_list) that:
   - Calls insert_lead() for each lead in the list
   - Returns a summary dict: {inserted: N, skipped: N, errors: N}
5. Define get_lead_count() that returns the total number of leads in the table
6. Add a __main__ block that:
   - Creates one mock lead dict with all 15 fields populated with realistic test data
   - Calls insert_lead() with it
   - Calls insert_lead() again with the SAME phone number to test deduplication
   - Calls get_lead_count() and prints the total
   - Prints "Stage 7 passed — Supabase connected and deduplication working"

Use python-dotenv to load credentials.
Run it and show me the output including the Supabase response.
```

**What success looks like:**
- First insert succeeds
- Second insert with same phone is silently skipped (not an error)
- Lead count shows 1, not 2
- No authentication errors

---

### Stage 8 — Email Enrichment

**Goal:** Given a business website URL, scrape the page and find any email address. This is the fallback when Google profile has no email.

**Instructions for Claude Code:**
```
Create enrichment/email.py for the Altrium scraper.

This file must:
1. Import httpx, re, and tenacity
2. Define find_email_on_website(website_url, timeout=10) that:
   - Makes an HTTP GET request to the website URL using httpx
   - Searches the response HTML for email addresses using regex:
     [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
   - Filters out common false positives:
     * emails ending in .png, .jpg, .gif, .webp
     * emails containing "example", "domain", "test", "sentry", "wix"
     * emails starting with noreply, no-reply, support@sentry
   - Returns the first valid email found, or None
   - Uses tenacity to retry up to 3 times on connection errors with 2s wait
   - Has a timeout of 10 seconds — never hang
   - Catches all exceptions and returns None (never crashes the main scraper)

3. Define enrich_business_email(business_dict) that:
   - Checks if business_dict already has a business_email — if so, returns as-is
   - If not, calls find_email_on_website() with the business website URL
   - Updates business_dict["business_email"] with the result
   - Returns the updated dict

4. Add a __main__ block that:
   - Tests on 3 real business website URLs (pick any 3 small business sites)
   - Prints the email found or "No email found" for each
   - Prints "Stage 8 passed"

Run it and show me the output.
```

**What success looks like:**
- At least 1 of the 3 test sites returns an email
- Timeouts are handled gracefully (no crashes)
- Invalid emails are filtered out

---

### Stage 9 — Config Files (Verticals + Cities)

**Goal:** Create the full list of 57 verticals and a comprehensive US cities list structured for the scraper loop.

**Instructions for Claude Code:**
```
Create config/verticals.py and config/cities.py for the Altrium scraper.

config/verticals.py must:
1. Define VERTICALS as a list of all 57 Altrium verticals exactly as specified:

HOME_SERVICES = [
    "plumber", "roofer", "HVAC contractor", "electrician", "tree service",
    "pest control", "concrete contractor", "water damage restoration",
    "pool service", "garage door company", "moving company",
    "landscaping company", "fence company", "tile contractor",
    "flooring company", "painting contractor", "general contractor",
    "home remodeling company", "bathroom remodeling company",
    "kitchen remodeling company", "window replacement company",
    "siding contractor", "gutter company", "demolition company",
    "asphalt paving company", "welding service"
]

HEALTHCARE = [
    "dentist", "orthodontist", "oral surgeon", "chiropractor", "med spa",
    "plastic surgeon", "cosmetic dentist", "dermatologist",
    "physical therapist", "family doctor", "urgent care", "podiatrist"
]

LEGAL = [
    "car accident lawyer", "personal injury lawyer", "family lawyer",
    "divorce lawyer", "criminal defense lawyer", "estate planning lawyer",
    "immigration lawyer", "real estate lawyer", "business lawyer",
    "tax attorney", "bankruptcy lawyer", "civil litigation lawyer",
    "employment lawyer"
]

FINANCIAL = [
    "financial advisor", "insurance agent", "mortgage broker",
    "tax accountant", "CPA", "bookkeeper", "wealth management",
    "retirement planning"
]

VERTICALS = HOME_SERVICES + HEALTHCARE + LEGAL + FINANCIAL

2. Define VERTICAL_CATEGORY = a dict mapping each vertical string to its category name

config/cities.py must:
1. Define CITIES as a list of dicts, each with:
   {"city": "Houston", "state": "TX"}
2. Include at minimum the top 100 US cities by population
3. Structure it so cities can be filtered by state:
   get_cities_by_state(state_code) returns just that state's cities
4. Add a START_CITY index variable = 0 (used to resume if scraper stops mid-run)

Add a __main__ block to each file that prints a summary count and samples.
Run both and confirm 57 verticals and 100+ cities load correctly.
```

**What success looks like:**
- Exactly 57 verticals in VERTICALS list
- 100+ cities loaded
- get_cities_by_state("TX") returns Texas cities only

---

### Stage 10 — Main Pipeline (Full End-to-End)

**Goal:** Wire all stages together into main.py. Run one complete vertical + city search end to end, from Google Maps to Supabase.

**Instructions for Claude Code:**
```
Create main.py for the Altrium scraper — the full pipeline entry point.

This file must:
1. Import all modules from previous stages
2. Set up logging to both console and logs/scraper.log
3. Define run_search(vertical, city, state) that runs one complete search:
   a. Launch browser with proxy
   b. Search Google Maps for "{vertical} in {city}, {state}"
   c. Scrape all business listings
   d. For each business that passes the base filter (3.0–4.9 stars, 15+ reviews):
      - Get business details (phone, address, city, state)
      - Scrape 50 most recent reviews
      - Process review dates
      - Run qualify_business() — skip if None returned
      - Enrich email
      - Format phone to E.164
      - Build the full 15-field lead dict
      - Insert to Supabase via insert_lead()
   e. Close browser
   f. Return summary: {searched: N, qualified: N, inserted: N, skipped_dupe: N}

4. Define run_full_pipeline(verticals=None, cities=None) that:
   - Defaults to all 57 VERTICALS and all CITIES if not specified
   - Loops through every combination
   - Calls run_search() for each
   - Waits a random 5–15 seconds between searches (human-like pacing)
   - Logs progress after each search
   - Saves a checkpoint after each city so it can resume if interrupted

5. Add a __main__ block with two modes controlled by a TEST_MODE flag:
   - TEST_MODE = True → runs ONE search: "plumber in Austin, TX"
     Prints full output, saves to logs/test_run.json, shows Supabase count
   - TEST_MODE = False → runs the full pipeline

Start with TEST_MODE = True.
Run it and show me the complete output from start to finish.
Print "ALL STAGES COMPLETE — SCRAPER WORKING" if the test run succeeds.
```

**What success looks like:**
- Browser opens, searches Google Maps
- At least one business passes all filters
- At least one signal fires
- Lead appears in Supabase database
- All 15 fields populated correctly
- No unhandled exceptions

---

## Common Errors and Fixes

| Error | Likely cause | Fix |
|---|---|---|
| `playwright._impl._errors.TimeoutError` | Element not found in time | Increase timeout, check selector |
| `ModuleNotFoundError` | Package not installed | Run pip install inside venv |
| `CAPTCHA detected` | Google blocked the request | Enable proxy, check stealth setup |
| `supabase.exceptions.APIError` | Wrong Supabase credentials | Check .env values match Supabase dashboard |
| `phonenumbers.NumberParseException` | Phone number in unexpected format | format_phone_e164 handles this — returns raw |
| `httpx.ConnectTimeout` | Website too slow | Already handled by tenacity retry + timeout |
| Empty results from Google Maps | Selector changed | Update selector in maps.py |
| `IndexError` on review scrape | Fewer reviews than expected | Already handled by max_reviews cap |

---

## After All 10 Stages Pass

Once the full pipeline runs successfully on one vertical + city:

1. Set `TEST_MODE = False` in main.py
2. Start with 2–3 states to validate at scale before running full USA
3. Monitor logs/scraper.log for errors
4. Check Supabase dashboard to confirm leads are populating correctly
5. Add n8n scheduling (separate guide) to run automatically every Monday

---

## Important Notes

- **Never commit .env to git** — it contains your proxy and Supabase credentials
- **Run inside the virtual environment** — always activate with `source venv/bin/activate` first
- **Decodo proxies required from Stage 3 onwards** — without them Google will block at scale
- **Supabase free tier** holds ~500MB of data — roughly 500,000 leads before needing to upgrade
- **Random delays between requests** are critical — the scraper must behave like a human
- **If a stage fails** — fix it completely before moving to the next one
- **Google Maps selectors can change** — if results suddenly stop working, the HTML structure may have changed and selectors in maps.py or reviews.py need updating