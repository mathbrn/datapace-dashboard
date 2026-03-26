#!/usr/bin/env python3
"""
Crawler RunSignUp — extrait les finishers pour les courses US du dashboard.

RunSignUp API:
  - Search: /Rest/races?format=json&name=EVENT
  - Events: /Rest/race/{raceId}?format=json&include_event_days=T
  - Results: /Rest/race/{raceId}/results/get-results?format=json&event_id={eventId}&page=999&num_results=50

Le total de finishers = place du dernier resultat sur la derniere page.

Usage:
    python crawl_runsignup.py
"""

import sys
import io
import json
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR / "runsignup_crawl_results.json"

BASE = "https://runsignup.com/Rest"

# Mapping: Excel event name -> RunSignUp search query + race_id (if known)
TARGETS = [
    # (excel_name, excel_dist, runsignup_race_id, event_name_filter, years_needed)
    ("Ukrop's Monument Avenue 10K", "10KM", 53948, "Monument Avenue 10k", range(2016, 2023)),
    ("Statesman Capitol 10K", "10KM", None, "Cap10K", range(2010, 2018)),
    ("Atlanta Journal-Constitution Peachtree Road Race", "10KM", None, "Peachtree Road Race", [2019]),
    ("IU Health 500 Festival Mini-Marathon", "SEMI", None, "500 Festival Mini-Marathon", range(2010, 2020)),
    ("Rock 'n' Roll Running Series Las Vegas", "SEMI", None, "Rock n Roll Las Vegas", range(2010, 2020)),
    ("Walt Disney World Marathon Weekend", "SEMI", None, "Disney World Half Marathon", range(2010, 2020)),
    ("Disney Princess Half Marathon", "SEMI", None, "Disney Princess Half", range(2010, 2020)),
    ("NYRR RBC Brooklyn Half", "SEMI", None, "Brooklyn Half", range(2016, 2020)),
    ("Aramco Houston Half Marathon", "SEMI", None, "Houston Half Marathon", range(2020, 2024)),
    ("St. Jude Rock 'n' Roll Series Nashville", "SEMI", None, "Rock n Roll Nashville", [2010, 2012, 2013, 2017, 2023, 2024]),
    ("St. Jude Rock 'n' Roll Running Series Washington DC", "SEMI", None, "Rock n Roll Washington DC", range(2010, 2020)),
    ("Rock 'n' Roll Running Series San Diego", "SEMI", None, "Rock n Roll San Diego", range(2010, 2020)),
    ("Eugene Marathon", "MARATHON", None, "Eugene Marathon", []),
    ("Medtronic Twin Cities Marathon", "MARATHON", None, "Twin Cities Marathon", [2000]),
    ("Long Beach Marathon", "MARATHON", None, "Long Beach Marathon", range(2010, 2020)),
    ("BMW Dallas Marathon", "MARATHON", None, "Dallas Marathon", range(2010, 2020)),
    ("Denver Colfax Marathon", "MARATHON", None, "Colfax Marathon", range(2010, 2020)),
    ("Fargo Marathon", "MARATHON", None, "Fargo Marathon", range(2010, 2020)),
]


def api_get(path, retries=2):
    """GET request to RunSignUp API."""
    url = f"{BASE}{path}"
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "DataPace-Dashboard/1.0"})
            resp = urlopen(req, timeout=15)
            return json.loads(resp.read().decode())
        except HTTPError as e:
            if e.code == 429:  # Rate limited
                wait = 10 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif e.code == 403:
                return None
            else:
                return None
        except (URLError, TimeoutError):
            if attempt < retries:
                time.sleep(3)
            else:
                return None
    return None


def search_race(name):
    """Search for a race by name, return race_id."""
    data = api_get(f"/races?format=json&results_per_page=5&name={name.replace(' ', '+')}")
    if not data:
        return None
    for race_entry in data.get("races", []):
        r = race_entry.get("race", {})
        return r.get("race_id")
    return None


def get_race_events(race_id):
    """Get all events (years) for a race."""
    data = api_get(f"/race/{race_id}?format=json&include_event_days=T")
    if not data:
        return []
    race = data.get("race", {})
    events = race.get("events", [])
    result = []
    for e in events:
        eid = e.get("event_id")
        ename = e.get("name", "")
        etype = e.get("event_type", "")
        dist = e.get("distance", "")
        start = e.get("start_time", "")
        if etype == "virtual_race":
            continue
        # Extract year from name or start_time
        import re
        year_match = re.search(r"20\d{2}", ename + " " + start)
        year = int(year_match.group()) if year_match else None
        result.append({
            "event_id": eid,
            "name": ename,
            "year": year,
            "distance": dist,
            "start": start,
        })
    return result


def get_finisher_count(race_id, event_id):
    """Get the total number of finishers for a specific event."""
    # First, get the result sets
    data = api_get(f"/race/{race_id}/results/get-results?format=json&event_id={event_id}&page=1&num_results=1")
    if not data:
        return None

    for rs in data.get("individual_results_sets", []):
        rs_id = rs.get("individual_result_set_id")
        if not rs_id:
            continue

        # Binary search for the last page
        # Start with a high page estimate
        low, high = 1, 2000
        last_place = 0

        # First try page 1 to see if there are results
        test = api_get(f"/race/{race_id}/results/get-results?format=json&event_id={event_id}&individual_result_set_id={rs_id}&page=1&num_results=50")
        if not test:
            continue
        test_rs = test.get("individual_results_sets", [{}])[0]
        results = test_rs.get("results", [])
        if not results:
            continue

        # Try progressively higher pages to find the end
        for page in [10, 50, 100, 200, 500, 1000]:
            test = api_get(f"/race/{race_id}/results/get-results?format=json&event_id={event_id}&individual_result_set_id={rs_id}&page={page}&num_results=50")
            if not test:
                break
            test_rs = test.get("individual_results_sets", [{}])[0]
            results = test_rs.get("results", [])
            if not results:
                # Last valid page is somewhere before this
                high = page
                break
            else:
                low = page
                last_result = results[-1]
                last_place = last_result.get("place", 0)
                if isinstance(last_place, str):
                    try:
                        last_place = int(last_place)
                    except ValueError:
                        last_place = 0

        # Binary search between low and high
        while low < high - 1:
            mid = (low + high) // 2
            test = api_get(f"/race/{race_id}/results/get-results?format=json&event_id={event_id}&individual_result_set_id={rs_id}&page={mid}&num_results=50")
            if not test:
                high = mid
                continue
            test_rs = test.get("individual_results_sets", [{}])[0]
            results = test_rs.get("results", [])
            if results:
                low = mid
                last_result = results[-1]
                p = last_result.get("place", 0)
                if isinstance(p, str):
                    try:
                        p = int(p)
                    except ValueError:
                        p = 0
                last_place = max(last_place, p)
            else:
                high = mid

        # Get the actual last page
        test = api_get(f"/race/{race_id}/results/get-results?format=json&event_id={event_id}&individual_result_set_id={rs_id}&page={low}&num_results=50")
        if test:
            test_rs = test.get("individual_results_sets", [{}])[0]
            results = test_rs.get("results", [])
            if results:
                last_result = results[-1]
                p = last_result.get("place", 0)
                if isinstance(p, str):
                    try:
                        p = int(p)
                    except ValueError:
                        p = 0
                last_place = max(last_place, p)

        if last_place > 0:
            return last_place

    return None


def main():
    print("=" * 60)
    print("  RunSignUp Crawler — Finisher Counts")
    print("=" * 60)
    print()

    all_results = []
    total_found = 0

    for excel_name, excel_dist, race_id, search_query, years_needed in TARGETS:
        years_list = list(years_needed)
        if not years_list:
            continue

        print(f">>> {excel_name} ({excel_dist})")

        # Find race_id if not provided
        if not race_id:
            race_id = search_race(search_query)
            if not race_id:
                print(f"    Race not found for '{search_query}'")
                print()
                continue
            print(f"    Found race_id: {race_id}")

        # Get all events for this race
        events = get_race_events(race_id)
        if not events:
            print(f"    No events found")
            print()
            race_id = None  # Reset for next search
            continue

        # Match events to needed years
        for year in years_list:
            matching = [e for e in events if e["year"] == year and "virtual" not in e["name"].lower()]
            if not matching:
                continue

            # Take the first matching non-virtual event
            event = matching[0]
            eid = event["event_id"]

            print(f"    {year}: event_id={eid} ({event['name'][:50]})")

            count = get_finisher_count(race_id, eid)
            if count and count > 50:  # Minimum threshold
                print(f"    -> {count} finishers")
                all_results.append({
                    "excel_name": excel_name,
                    "excel_dist": excel_dist,
                    "year": year,
                    "finishers": count,
                    "event_id": eid,
                    "event_name": event["name"],
                    "source": "runsignup",
                })
                total_found += 1
            else:
                print(f"    -> No results or count too low ({count})")

            time.sleep(1)  # Rate limiting

        race_id = None  # Reset for next target (search again)
        print()

    # Save results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": total_found,
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)

    print(f"{'=' * 60}")
    print(f"  Total: {total_found} finisher counts found")
    print(f"  Saved to: {OUTPUT_FILE}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
