import re
import sys
from pathlib import Path

# Prevent enrichment/ from shadowing stdlib 'email' module
_script_dir = str(Path(__file__).parent)
if _script_dir in sys.path:
    sys.path.remove(_script_dir)

sys.path.insert(0, str(Path(__file__).parent.parent))

import dns.resolver
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'\+?1?[\s.\-]?\(?(\d{3})\)?[\s.\-](\d{3})[\s.\-](\d{4})')

# Generic prefixes that indicate a shared inbox rather than a person
_GENERIC = {
    'info', 'contact', 'admin', 'support', 'hello', 'hi', 'team',
    'office', 'mail', 'marketing', 'sales', 'help', 'billing',
    'accounts', 'reception', 'enquiries', 'enquiry', 'general',
    'webmaster', 'hostmaster', 'postmaster', 'abuse', 'privacy',
    'legal', 'press', 'media', 'news', 'pr', 'hr', 'jobs',
    'careers', 'service', 'services', 'care', 'feedback',
    'quotes', 'estimates', 'bookings', 'reservations', 'manager',
    'management', 'customercare', 'customerservice', 'cs',
    'tech', 'digital', 'hello', 'website', 'web', 'home',
}

_INVALID_EXTENSIONS = ('.png', '.jpg', '.gif', '.webp', '.svg', '.ico')
_INVALID_KEYWORDS   = ('example', 'domain', 'test', 'sentry', 'wix')
_INVALID_PREFIXES   = ('noreply', 'no-reply', 'support@sentry')


def _is_valid_email(email):
    lower = email.lower()
    if any(lower.endswith(ext) for ext in _INVALID_EXTENSIONS):
        return False
    if any(kw in lower for kw in _INVALID_KEYWORDS):
        return False
    if any(lower.startswith(prefix) for prefix in _INVALID_PREFIXES):
        return False
    return True


def _email_score(email):
    """Higher score = more likely to be a real named contact."""
    local = email.split('@')[0].lower()
    local_clean = re.sub(r'\d+$', '', local)

    if local_clean in _GENERIC:
        return 1

    # firstname.lastname or f.lastname pattern — strong named signal
    if re.match(r'^[a-z]{2,}\.[a-z]{2,}$', local):
        return 4

    # initial + lastname e.g. jsmith
    if re.match(r'^[a-z][a-z]{3,12}$', local) and local_clean not in _GENERIC:
        return 3

    # Single short word not in generic list — could be a name
    if re.match(r'^[a-z]{2,15}$', local):
        return 2

    return 1


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.RemoteProtocolError)),
    reraise=True,
)
def _fetch(url, timeout):
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        return response.text


def find_all_emails_on_website(website_url, timeout=10):
    """
    Returns all valid emails found on the page, sorted best-first.
    Named emails (john.smith@) rank above generic ones (info@).
    """
    try:
        html = _fetch(website_url, timeout)
        candidates = [e for e in EMAIL_RE.findall(html) if _is_valid_email(e)]
        seen = set()
        unique = [e for e in candidates if not (e.lower() in seen or seen.add(e.lower()))]
        return sorted(unique, key=_email_score, reverse=True)
    except Exception:
        return []


def find_all_phones_on_website(website_url, timeout=10):
    """
    Returns all unique US phone numbers found on the page in E.164 format.
    """
    try:
        html = _fetch(website_url, timeout)
        found = []
        seen = set()
        for m in PHONE_RE.finditer(html):
            e164 = f"+1{m.group(1)}{m.group(2)}{m.group(3)}"
            if e164 not in seen:
                seen.add(e164)
                found.append(e164)
        return found
    except Exception:
        return []


_DOMAIN_MAP = {
    "gmail.com":       "Gmail Personal",
    "googlemail.com":  "Gmail Personal",
    "yahoo.com":       "Yahoo Mail",
    "yahoo.co.uk":     "Yahoo Mail",
    "ymail.com":       "Yahoo Mail",
    "hotmail.com":     "Outlook Personal",
    "hotmail.co.uk":   "Outlook Personal",
    "live.com":        "Outlook Personal",
    "live.co.uk":      "Outlook Personal",
    "msn.com":         "Outlook Personal",
    "outlook.com":     "Outlook Personal",
    "comcast.net":     "Comcast",
    "att.net":         "AT&T Mail",
    "sbcglobal.net":   "AT&T Mail",
    "verizon.net":     "Verizon Mail",
    "cox.net":         "Cox Communications",
    "earthlink.net":   "EarthLink",
    "icloud.com":      "Apple iCloud",
    "me.com":          "Apple iCloud",
    "mac.com":         "Apple iCloud",
    "aol.com":         "AOL Mail",
    "protonmail.com":  "ProtonMail",
    "proton.me":       "ProtonMail",
    "zoho.com":        "Zoho Mail",
    "zohomail.com":    "Zoho Mail",
    "fastmail.com":    "Fastmail",
    "iinet.net.au":    "iiNet",
    "bigpond.com":     "Telstra",
    "charter.net":     "Spectrum",
    "roadrunner.com":  "Spectrum",
}


def detect_email_provider(email):
    """
    Returns the email hosting provider name.
    Checks known consumer domains first, then MX records for business domains.
    """
    if not email or "@" not in email:
        return "Unknown"

    domain = email.split("@")[1].lower()

    # Check known consumer/ISP domains directly
    if domain in _DOMAIN_MAP:
        return _DOMAIN_MAP[domain]

    # Fall back to MX record lookup for custom business domains
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        for rdata in answers:
            mx = str(rdata.exchange).lower()
            if "google" in mx or "googlemail" in mx:
                return "Google Workspace"
            if "outlook" in mx or "microsoft" in mx or "protection.outlook" in mx:
                return "Microsoft 365"
            if "zoho" in mx:
                return "Zoho Mail"
            if "protonmail" in mx:
                return "ProtonMail"
            if "fastmail" in mx:
                return "Fastmail"
            if "mxroute" in mx:
                return "MXroute"
            if "amazonses" in mx or "amazonaws" in mx:
                return "Amazon SES"
        return "Other"
    except Exception:
        return "Unknown"


def enrich_business_email(business_dict):
    """
    Scrapes all emails and phones from the business website.
    - business_email  → best email (named contact wins over generic)
    - all_emails      → comma-separated list of every email found, named first
    - phone           → kept from Google Maps; supplemented from website if missing
    - all_phones      → comma-separated list of every phone found on website
    """
    website = business_dict.get("website")
    if not website:
        return business_dict

    emails = find_all_emails_on_website(website)
    if emails:
        business_dict["business_email"] = emails[0]
        business_dict["all_emails"] = ", ".join(emails)

    phones = find_all_phones_on_website(website)
    if phones:
        business_dict["all_phones"] = ", ".join(phones)
        if not business_dict.get("phone"):
            business_dict["phone"] = phones[0]

    # Detect email provider from MX records
    best_email = business_dict.get("business_email")
    business_dict["email_provider"] = detect_email_provider(best_email) if best_email else "Unknown"

    return business_dict


# Keep single-result helpers for backwards compatibility
def find_email_on_website(website_url, timeout=10):
    results = find_all_emails_on_website(website_url, timeout)
    return results[0] if results else None


def find_phone_on_website(website_url, timeout=10):
    results = find_all_phones_on_website(website_url, timeout)
    return results[0] if results else None


if __name__ == "__main__":
    # --- Email scoring test ---
    print("=== Email scoring test ===")
    test_emails = [
        "john.smith@austinplumbing.com",   # named — should win
        "jsmith@austinplumbing.com",        # likely named
        "info@austinplumbing.com",          # generic
        "contact@austinplumbing.com",       # generic
    ]
    for e in test_emails:
        print(f"  score={_email_score(e)}  {e}")

    # --- Direct HTML extraction test ---
    print("\n=== Direct HTML extraction test ===")
    cases = [
        ('<p>Email mike.jones@bestplumber.com or info@bestplumber.com</p>',
         "mike.jones@bestplumber.com"),   # named should beat generic
        ('<a href="mailto:contact@roofer.net">Contact</a> or call jdoe@roofer.net',
         "jdoe@roofer.net"),
        ('<img src="logo@2x.png"> noreply@x.com example@test.com', None),
    ]
    all_passed = True
    for html, expected in cases:
        emails = [e for e in EMAIL_RE.findall(html) if _is_valid_email(e)]
        found = max(emails, key=_email_score) if emails else None
        status = "✓" if found == expected else "✗"
        print(f"  {status}  expected={expected!r}  got={found!r}")
        if found != expected:
            all_passed = False

    # --- Live URL test ---
    print("\n=== Live URL test ===")
    url = "https://www.callmrplumber.com"
    email = find_email_on_website(url)
    phone = find_phone_on_website(url)
    print(f"  {url}")
    print(f"    email → {email}")
    print(f"    phone → {phone}")

    print()
    if all_passed:
        print("Stage 8 (enhanced) passed — named email prioritisation working")
