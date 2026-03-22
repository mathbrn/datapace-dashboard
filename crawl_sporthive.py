#!/usr/bin/env python3
"""
Mass crawler for Sporthive/MYLAPS events.
Discovers events by scanning ID ranges and extracts finisher counts + avg times.

Strategy: Sporthive event IDs are 64-bit snowflake-like IDs.
Known IDs cluster in ranges. We scan around known IDs to discover new events.

Output: sporthive_crawl_results.json
"""
import json
import urllib.request
import ssl
import time
import sys
import os

API_BASE = "https://eventresults-api.speedhive.com/sporthive/events"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "sporthive_crawl_results.json")

# Known event IDs as seed points (from our previous work)
SEEDS = [
    6181850543435022336, 6232162395931082240, 6313393060860395776,
    6376355623617494016, 6378318208959589120, 6386505967023513344,
    6447830197266687232, 6501067205981731328, 6509035005995656960,
    6578568117027278336, 6589788263981649920, 6641699407497361920,
    6847176823684695296, 6853741552290238720, 6854892113662505728,
    6855879561074155264, 6899385745755210752, 6907012645799442176,
    6914931831426482176, 6968223295870065664, 6975382507753810176,
    6976159278361190656, 6981282006063051264, 6983192910261964288,
    6984850175007181568, 6996060929284046336, 7031189930019023616,
    7034488838654257408, 7034597458377179392, 7037394564091167232,
    7039548795219704576, 7049372004225601280, 7053750963571596288,
    7107027636359228672, 7107378500659252480, 7113512886511920128,
    7114588810278565120, 7115610136352492288, 7120011429951427328,
    7142907578304137472, 7142910812398577664, 7148258785540036096,
    7150153523280253696, 7168235550385003776, 7170462228881917696,
    7180618688493574912, 7183110323454187008, 7231234663007034112,
    7231246319547842560, 7242466977444592384, 7250456063290378496,
    7250556144618307584, 7250558163252939008, 7315035702770155264,
    7318184016761806336, 7373325160560043008, 7375922975814115328,
    7376930609500782592, 7383449171605338624, 7391336032891165440,
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_event(event_id):
    """Fetch races for a Sporthive event ID."""
    url = f"{API_BASE}/{event_id}/races"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return data
    except Exception:
        pass
    return None


def extract_event_info(event_id, races):
    """Extract useful info from race data."""
    results = []
    for race in races:
        name = race.get("raceName", "")
        dist = race.get("distanceInMeter", 0)
        count = race.get("classificationsCount", 0)
        stats = race.get("raceStatistics", {})
        avg_speed = stats.get("averageSpeedInKmh", 0)
        date = race.get("date", "")[:10]

        # Only keep running races with 100+ finishers, 5K+
        if count < 100 or dist < 5000:
            continue
        # Skip business runs, relays, kids, etc.
        skip_words = ["business", "relay", "estafette", "duo", "kampioenschap",
                      "elite", "scholieren", "campeonato", "kid", "junior", "walking"]
        if any(w in name.lower() for w in skip_words):
            continue

        # Compute average time from speed
        avg_time = None
        if avg_speed > 0 and dist > 0:
            dist_km = dist / 1000
            avg_hours = dist_km / avg_speed
            h = int(avg_hours)
            m = int((avg_hours - h) * 60)
            s = int(((avg_hours - h) * 60 - m) * 60)
            avg_time = f"{h}:{m:02d}:{s:02d}"

        results.append({
            "event_id": str(event_id),
            "race_name": name,
            "distance_m": dist,
            "date": date,
            "finishers": count,
            "avg_time": avg_time,
            "avg_speed_kmh": round(avg_speed, 2) if avg_speed else None,
        })
    return results


def scan_range(start_id, end_id, step, all_results, seen_ids):
    """Scan a range of event IDs."""
    found = 0
    for eid in range(start_id, end_id, step):
        if eid in seen_ids:
            continue
        seen_ids.add(eid)
        races = fetch_event(eid)
        if races:
            infos = extract_event_info(eid, races)
            if infos:
                all_results.extend(infos)
                found += len(infos)
                first = infos[0]
                print(f"  FOUND {eid}: {first['race_name']} ({first['date']}) "
                      f"= {first['finishers']} finishers", flush=True)
    return found


def main():
    print("Sporthive Mass Crawler")
    print("=" * 50)

    # Load existing results
    all_results = []
    seen_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            all_results = json.load(f)
        seen_ids = set(r["event_id"] for r in all_results)
        print(f"Loaded {len(all_results)} existing results ({len(seen_ids)} events)")

    # Phase 1: Scan known seeds
    print("\n--- Phase 1: Known seeds ---")
    for seed in SEEDS:
        if str(seed) in seen_ids:
            continue
        races = fetch_event(seed)
        if races:
            infos = extract_event_info(seed, races)
            if infos:
                all_results.extend(infos)
                seen_ids.add(str(seed))

    # Phase 2: Scan around known IDs (± offsets)
    # Sporthive IDs are not sequential but events created close in time
    # have IDs in similar ranges
    print("\n--- Phase 2: Scanning around known IDs ---")
    offsets = list(range(-50, 51))  # ±50 around each seed
    # Use larger steps for efficiency
    step_sizes = [
        1,                    # exact neighbors
        1024,                 # small jumps
        1048576,              # ~1M jumps
        1073741824,           # ~1B jumps
        4294967296,           # ~4B jumps
    ]

    total_found = 0
    for seed in SEEDS[:20]:  # Start with first 20 seeds
        for offset in [-4294967296, -1073741824, -1048576, -1024, -1,
                       1, 1024, 1048576, 1073741824, 4294967296]:
            eid = seed + offset
            if eid <= 0 or str(eid) in seen_ids:
                continue
            seen_ids.add(str(eid))
            races = fetch_event(eid)
            if races:
                infos = extract_event_info(eid, races)
                if infos:
                    all_results.extend(infos)
                    total_found += len(infos)
                    first = infos[0]
                    print(f"  FOUND {eid}: {first['race_name']} ({first['date']}) "
                          f"= {first['finishers']}", flush=True)

    # Phase 3: Systematic scan of high-density ranges
    print("\n--- Phase 3: Systematic range scan ---")
    # IDs 6.1e18 to 7.4e18 contain most events (2016-2026)
    # Scan with large steps first, then refine around hits
    scan_starts = [
        (6100000000000000000, 6200000000000000000, 10000000000000000),
        (6200000000000000000, 6400000000000000000, 10000000000000000),
        (6400000000000000000, 6600000000000000000, 10000000000000000),
        (6600000000000000000, 6800000000000000000, 10000000000000000),
        (6800000000000000000, 7000000000000000000, 10000000000000000),
        (7000000000000000000, 7200000000000000000, 10000000000000000),
        (7200000000000000000, 7400000000000000000, 10000000000000000),
    ]

    for start, end, step in scan_starts:
        found = scan_range(start, end, step, all_results, seen_ids)
        if found:
            print(f"  Range {start/1e18:.1f}e18 - {end/1e18:.1f}e18: {found} races found")

    # Save results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Total races found: {len(all_results)}")
    print(f"Unique events: {len(seen_ids)}")
    total_finishers = sum(r["finishers"] for r in all_results)
    print(f"Total finishers: {total_finishers:,}")

    # Top events by finishers
    top = sorted(all_results, key=lambda x: -x["finishers"])[:20]
    print(f"\nTop 20 by finishers:")
    for r in top:
        print(f"  {r['finishers']:>8,} | {r['race_name'][:40]} | {r['date']}")


if __name__ == "__main__":
    main()
