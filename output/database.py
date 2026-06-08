import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def insert_lead(lead_dict):
    client = get_supabase_client()
    try:
        response = client.table("leads").upsert(
            lead_dict,
            on_conflict="phone",
            ignore_duplicates=True,
        ).execute()

        if response.data:
            logging.info(f"Inserted: {lead_dict.get('business_name')} ({lead_dict.get('phone')})")
            return True
        else:
            logging.info(f"Skipped duplicate: {lead_dict.get('phone')}")
            return False
    except Exception as e:
        logging.error(f"Error inserting lead: {e}")
        return False


def insert_leads_batch(leads_list):
    summary = {"inserted": 0, "skipped": 0, "errors": 0}
    for lead in leads_list:
        try:
            inserted = insert_lead(lead)
            if inserted:
                summary["inserted"] += 1
            else:
                summary["skipped"] += 1
        except Exception as e:
            logging.error(f"Batch error: {e}")
            summary["errors"] += 1
    return summary


def get_lead_count():
    client = get_supabase_client()
    response = client.table("leads").select("id", count="exact").execute()
    return response.count


if __name__ == "__main__":
    mock_lead = {
        "business_name": "Test Plumbing Co",
        "phone": "+15550000001",
        "business_email": "test@testplumbing.com",
        "city": "Austin",
        "state": "TX",
        "vertical": "plumber",
        "qualifying_signal": "a",
        "star_rating": 4.1,
        "total_reviews": 47,
        "bad_review_date": "2026-05-01",
        "bad_review_stars": 2,
        "bad_review_text": "Showed up late and left a mess.",
        "bad_review_author": "Jane Doe",
        "days_since_last_response": 62,
        "maps_url": "https://www.google.com/maps/place/test",
    }

    print("Inserting first lead...")
    result1 = insert_lead(mock_lead)
    print(f"  Result: {'inserted' if result1 else 'skipped'}")

    print("Inserting same phone again (deduplication test)...")
    result2 = insert_lead(mock_lead)
    print(f"  Result: {'inserted' if result2 else 'skipped (duplicate — correct)'}")

    count = get_lead_count()
    print(f"\nTotal leads in database: {count}")

    if result1 and not result2:
        print("\nStage 7 passed — Supabase connected and deduplication working")
    else:
        print("\nCheck results above — unexpected insert/skip behavior")
