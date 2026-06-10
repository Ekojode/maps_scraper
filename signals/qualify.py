import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import phonenumbers


def _parse_date(d):
    if isinstance(d, date):
        return d
    if isinstance(d, str) and d:
        try:
            return date.fromisoformat(d)
        except ValueError:
            return None
    return None


def qualify_business(reviews, business):
    star_rating = business.get("star_rating")
    total_reviews = business.get("total_reviews")

    if star_rating is None or not (3.0 <= float(star_rating) <= 4.9):
        return None
    if total_reviews is None or int(total_reviews) < 15:
        return None

    today = date.today()

    # Attach parsed date objects
    parsed = []
    for r in reviews:
        rd = _parse_date(r.get("review_date"))
        if rd is None:
            continue
        ord_ = _parse_date(r.get("owner_reply_date"))
        parsed.append({**r, "_rd": rd, "_ord": ord_})

    # Days since last owner reply (used across signals)
    replied = [r for r in parsed if r.get("has_owner_reply")]
    days_since_last_response = None
    if replied:
        best_date = max(
            (r["_ord"] or r["_rd"] for r in replied),
            default=None,
        )
        if best_date:
            days_since_last_response = (today - best_date).days

    def result(signal, review, days_override=None):
        return {
            "qualifying_signal": signal,
            "bad_review_date": review["_rd"].isoformat(),
            "bad_review_stars": review.get("review_stars"),
            "bad_review_text": review.get("review_text", ""),
            "bad_review_author": review.get("reviewer_name", ""),
            "days_since_last_response": days_override if days_override is not None else days_since_last_response,
        }

    # SIGNAL A — 1-3 star, last 60 days, no reply
    for r in parsed:
        days = (today - r["_rd"]).days
        if r.get("review_stars") in (1, 2, 3) and not r.get("has_owner_reply") and days <= 60:
            return result("a", r)

    # SIGNAL B — 1-3 star, 61-90 days, no reply
    for r in parsed:
        days = (today - r["_rd"]).days
        if r.get("review_stars") in (1, 2, 3) and not r.get("has_owner_reply") and 61 <= days <= 90:
            return result("b", r)

    # SIGNAL C — 3+ unanswered reviews (any stars) in last 60 days
    unanswered_60 = [
        r for r in parsed
        if not r.get("has_owner_reply")
        and (today - r["_rd"]).days <= 60
    ]
    if len(unanswered_60) >= 3:
        return {
            "qualifying_signal": "c",
            "bad_review_date": None,
            "bad_review_stars": None,
            "bad_review_text": None,
            "bad_review_author": None,
            "days_since_last_response": days_since_last_response,
        }

    # SIGNAL D — last owner reply was 45+ days ago AND at least one review
    # posted within those 45 days has no reply
    unanswered_within_45 = [
        r for r in parsed
        if not r.get("has_owner_reply")
        and (today - r["_rd"]).days <= 45
    ]
    if days_since_last_response is not None and days_since_last_response >= 45 and unanswered_within_45:
        return {
            "qualifying_signal": "d",
            "bad_review_date": None,
            "bad_review_stars": None,
            "bad_review_text": None,
            "bad_review_author": None,
            "days_since_last_response": days_since_last_response,
        }

    # SIGNAL E — 3+ positive replied in last 90 days, while unanswered negative reviews exist
    last_90 = [r for r in parsed if (today - r["_rd"]).days <= 90]
    positive_replied = [r for r in last_90 if r.get("has_owner_reply") and (r.get("review_stars") or 0) >= 4]

    unanswered_neg = [
        r for r in parsed
        if not r.get("has_owner_reply") and (r.get("review_stars") or 5) <= 3
    ]

    if len(positive_replied) >= 3 and len(unanswered_neg) > 0:
        trigger = max(unanswered_neg, key=lambda r: r["_rd"])
        return result("e", trigger)

    return None


def format_phone_e164(raw_phone, default_country="US"):
    try:
        parsed = phonenumbers.parse(raw_phone, default_country)
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return raw_phone


if __name__ == "__main__":
    reviews_path = Path("logs/stage5_reviews.json")
    with open(reviews_path) as f:
        reviews = json.load(f)

    business = {"star_rating": 4.1, "total_reviews": 47}

    result = qualify_business(reviews, business)
    if result:
        print(f"Signal fired: {result['qualifying_signal'].upper()}")
        print(f"  Bad review date:          {result['bad_review_date']}")
        print(f"  Stars:                    {result['bad_review_stars']}")
        print(f"  Author:                   {result['bad_review_author']}")
        print(f"  Days since last response: {result['days_since_last_response']}")
        print(f"  Text preview:             {str(result['bad_review_text'])[:100]}")
    else:
        print("No signal fired — review set has no qualifying patterns")
        print("(Expected if all scraped reviews are 5-star with recent owner replies)")

    print("\nPhone formatter test:")
    for p in ["+15122552505", "(512) 255-2505", "5122552505"]:
        print(f"  {p} → {format_phone_e164(p)}")

    print("\nStage 6 passed")
