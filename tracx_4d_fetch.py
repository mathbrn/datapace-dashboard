"""
Fetch 4D data (finishers, avg time, men winner, women winner) from Tracx Events API.
Uses systematic sampling (every Nth page) for average time computation.
API always returns 15 items per page regardless of per_page param.
"""
import requests
import json
import time as time_module
import math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://api.tracx.events/v1"
HEADERS = {"Authorization": "Bearer 40496C26-9BEF-4266-8A27-43C78540F669"}

# How many sample pages to fetch for avg time computation
TARGET_SAMPLE_PAGES = 100  # ~1500 results = good statistical sample

# Target events
TARGETS = [
    (114, 328, 1022, 1023, 1024, "Adidas Manchester Marathon", "MARATHON"),
    (42, 74, 236, 237, 238, "AJ Bell Great North Run", "SEMI"),
    (66, 120, 375, 376, 377, "AJ Bell Great Manchester Run", "SEMI"),
    (65, 118, 369, 370, 371, "AJ Bell Great Bristol Run", "SEMI"),
]

EVENT_YEARS = {42: 2021, 65: 2021, 66: 2021, 114: 2021}

TIME_RANGES = {
    "MARATHON": (2 * 3600, 8 * 3600),
    "SEMI": (3600, 4 * 3600),
    "10KM": (30 * 60, 2 * 3600),
}

DIST_KM = {"MARATHON": 42.195, "SEMI": 21.0975, "10KM": 10.0}
PAGE_SIZE = 15


def format_time(seconds):
    if seconds is None:
        return None
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def compute_chip_time(item):
    start_str = item.get('ranking_start') or item.get('start')
    finish_str = item.get('finish_time')
    if not start_str or not finish_str:
        return None
    try:
        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
            try:
                start = datetime.strptime(start_str, fmt)
                break
            except ValueError:
                continue
        else:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
            try:
                finish = datetime.strptime(finish_str, fmt)
                break
            except ValueError:
                continue
        else:
            return None
        delta = (finish - start).total_seconds()
        return delta if delta > 0 else None
    except Exception:
        return None


def get_json(url, params=None):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < 2:
                time_module.sleep(1)
            else:
                raise


def fetch_page(event_id, race_id, ranking_id, page):
    url = f"{BASE}/events/{event_id}/races/{race_id}/rankings/{ranking_id}/results"
    data = get_json(url, params={"page": page})
    return data.get('items', []) if isinstance(data, dict) else data


def fetch_pages_parallel(event_id, race_id, ranking_id, page_numbers):
    """Fetch multiple pages in parallel."""
    all_items = []
    # Process in batches of 10
    batch_size = 10
    for i in range(0, len(page_numbers), batch_size):
        batch = page_numbers[i:i+batch_size]
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(fetch_page, event_id, race_id, ranking_id, p): p
                for p in batch
            }
            for future in as_completed(futures):
                try:
                    items = future.result()
                    all_items.extend(items)
                except Exception as e:
                    pass
        time_module.sleep(0.05)
    return all_items


def get_ranking_meta(event_id, race_id, ranking_id):
    url = f"{BASE}/events/{event_id}/races/{race_id}/rankings/{ranking_id}/results"
    data = get_json(url, params={"page": 1})
    meta = data.get('meta', {}).get('pagination', {}) if isinstance(data, dict) else {}
    items = data.get('items', []) if isinstance(data, dict) else data
    return meta, items


def find_winner(event_id, race_id, ranking_id, time_min, time_max):
    page = 1
    while page <= 10:
        items = fetch_page(event_id, race_id, ranking_id, page)
        if not items:
            break
        for item in items:
            t = compute_chip_time(item)
            if t and time_min <= t <= time_max:
                name = f"{item.get('first_name', '')} {item.get('last_name', '')}".strip()
                return t, name
        page += 1
    return None, None


def main():
    print("=== Fetching 4D data from Tracx Events API ===")
    print(f"=== Sampling ~{TARGET_SAMPLE_PAGES} pages per ranking for avg time ===\n")

    all_4d_data = []

    for event_id, race_id, general_rid, male_rid, female_rid, dashboard_name, distance in TARGETS:
        print(f"\n{'='*60}")
        print(f"  {dashboard_name} ({distance})")
        print(f"  Event {event_id}, Race {race_id}")
        print(f"{'='*60}")

        year = EVENT_YEARS.get(event_id)
        time_min, time_max = TIME_RANGES[distance]

        # Get men's winner
        print(f"\n  Fetching men's winner (ranking {male_rid})...")
        men_winner_time, men_winner_name = find_winner(event_id, race_id, male_rid, time_min, time_max)
        if men_winner_time:
            print(f"    Men winner: {men_winner_name} - {format_time(men_winner_time)}")

        # Get women's winner
        print(f"\n  Fetching women's winner (ranking {female_rid})...")
        women_winner_time, women_winner_name = find_winner(event_id, race_id, female_rid, time_min, time_max)
        if women_winner_time:
            print(f"    Women winner: {women_winner_name} - {format_time(women_winner_time)}")

        # Get total finishers from meta
        print(f"\n  Fetching general ranking metadata (ranking {general_rid})...")
        meta, first_items = get_ranking_meta(event_id, race_id, general_rid)
        total_finishers = meta.get('total', 0)
        total_pages = meta.get('total_pages', 0)
        print(f"  Total finishers: {total_finishers} ({total_pages} pages)")

        # Determine which pages to sample
        if total_pages <= TARGET_SAMPLE_PAGES:
            # Small enough to fetch all
            pages_to_fetch = list(range(1, total_pages + 1))
        else:
            # Systematic sampling: evenly spaced pages
            step = total_pages / TARGET_SAMPLE_PAGES
            pages_to_fetch = [int(1 + i * step) for i in range(TARGET_SAMPLE_PAGES)]
            # Ensure page 1 and last page are included
            if 1 not in pages_to_fetch:
                pages_to_fetch[0] = 1
            if total_pages not in pages_to_fetch:
                pages_to_fetch[-1] = total_pages

        print(f"  Fetching {len(pages_to_fetch)} pages (out of {total_pages})...")

        all_items = fetch_pages_parallel(event_id, race_id, general_rid, pages_to_fetch)
        print(f"  Fetched {len(all_items)} sample items")

        finishers = total_finishers

        # Compute average time from sample
        total_time = 0
        valid_count = 0
        for item in all_items:
            t = compute_chip_time(item)
            if t and time_min <= t <= time_max:
                total_time += t
                valid_count += 1

        avg_seconds = total_time / valid_count if valid_count > 0 else None
        avg_speed = round(DIST_KM[distance] / (avg_seconds / 3600), 2) if avg_seconds else None

        print(f"  Valid times for avg: {valid_count}/{len(all_items)}")
        print(f"  Average time: {format_time(avg_seconds)}")
        print(f"  Average speed: {avg_speed} km/h")

        entry = {
            "event": dashboard_name,
            "distance": distance,
            "year": year,
            "finishers": finishers,
            "avg_time": format_time(avg_seconds),
            "avg_speed_kmh": avg_speed,
            "men_winner_time": format_time(men_winner_time),
            "men_winner_name": men_winner_name,
            "women_winner_time": format_time(women_winner_time),
            "women_winner_name": women_winner_name,
        }

        print(f"\n  RESULT: {json.dumps(entry, indent=2)}")
        all_4d_data.append(entry)

    # Save results
    out_path = r"C:\Users\mbrun\datapace-dashboard\tracx_4d_results.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_4d_data, f, indent=2, ensure_ascii=False)

    print(f"\n\n{'='*60}")
    print(f"DONE! Saved {len(all_4d_data)} entries to {out_path}")
    print(f"{'='*60}")

    for entry in all_4d_data:
        print(f"\n  {entry['event']} ({entry['distance']}, {entry['year']})")
        print(f"    Finishers: {entry['finishers']}")
        print(f"    Avg time: {entry['avg_time']} ({entry['avg_speed_kmh']} km/h)")
        print(f"    Men winner: {entry['men_winner_name']} - {entry['men_winner_time']}")
        print(f"    Women winner: {entry['women_winner_name']} - {entry['women_winner_time']}")


if __name__ == "__main__":
    main()
