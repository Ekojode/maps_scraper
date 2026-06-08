import csv
from pathlib import Path

START_CITY = 0

_CSV_PATH = Path(__file__).parent.parent / "uscities.csv"


def _load_cities():
    cities = []
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                pop = int(float(row["population"]))
            except (ValueError, KeyError):
                continue
            if pop < 10000:
                continue
            cities.append({
                "city":       row["city"],
                "state":      row["state_id"],
                "population": pop,
            })
    cities.sort(key=lambda c: c["population"], reverse=True)
    return cities


CITIES = _load_cities()


def get_cities_by_state(state_code):
    return [c for c in CITIES if c["state"] == state_code.upper()]


def get_top_cities(n):
    return CITIES[:n]


if __name__ == "__main__":
    print(f"Total cities loaded (population 10,000+): {len(CITIES)}")
    print(f"\nTop 10 by population:")
    for c in get_top_cities(10):
        print(f"  {c['city']}, {c['state']} — {c['population']:,}")

    # Breakdown by state
    from collections import Counter
    state_counts = Counter(c["state"] for c in CITIES)
    print(f"\nBreakdown by state ({len(state_counts)} states):")
    for state, count in sorted(state_counts.items()):
        print(f"  {state}: {count}")

    tx = get_cities_by_state("TX")
    print(f"\nTexas cities ({len(tx)}): {[c['city'] for c in tx[:10]]}...")
