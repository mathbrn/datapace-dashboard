"""
Fetch marathon/semi/10K results from TimeTo/SportInnovation API
and compute 4D stats: finishers, avg time, men's winner, women's winner.
"""

import requests
import json
import time as time_module
from datetime import timedelta

RACES = [
    {"event": "Schneider Electric Marathon de Paris", "distance": "MARATHON", "year": 2025, "raceId": 658},
    {"event": "Schneider Electric Marathon de Paris", "distance": "MARATHON", "year": 2024, "raceId": 318},
    {"event": "Harmonie Mutuelle Semi de Paris", "distance": "SEMI", "year": 2025, "raceId": 657},
    {"event": "Harmonie Mutuelle Semi de Paris", "distance": "SEMI", "year": 2024, "raceId": 313},
    {"event": "Hoka Semi de Paris", "distance": "SEMI", "year": 2026, "raceId": 806},
    {"event": "Run in Lyon", "distance": "SEMI", "year": 2025, "raceId": 635},
    {"event": "Run in Lyon", "distance": "MARATHON", "year": 2024, "raceId": 322},
    {"event": "Run in Lyon", "distance": "SEMI", "year": 2024, "raceId": 321},
    {"event": "Run in Lyon", "distance": "MARATHON", "year": 2023, "raceId": 368},
    {"event": "Run in Lyon", "distance": "SEMI", "year": 2023, "raceId": 369},
    {"event": "adidas 10K Paris", "distance": "10KM", "year": 2025, "raceId": 662},
    {"event": "adidas 10K Paris", "distance": "10KM", "year": 2024, "raceId": 319},
    {"event": "10K Montmartre", "distance": "10KM", "year": 2025, "raceId": 694},
]

DISTANCE_KM = {"MARATHON": 42.195, "SEMI": 21.0975, "10KM": 10.0}

# Time filters (in seconds)
TIME_FILTERS = {
    "MARATHON": (2 * 3600, 8 * 3600),       # 2h - 8h
    "SEMI":    (1 * 3600, 4 * 3600),         # 1h - 4h
    "10KM":    (0.5 * 3600, 2 * 3600),       # 30min - 2h
}

API_BASE = "https://sportinnovation.fr/api"
SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})


def parse_time_to_seconds(t):
    """Parse time string like '2:05:25' or '02:05:25' to total seconds."""
    if not t:
        return None
    t = t.strip()
    parts = t.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return None


def seconds_to_hhmmss(total_seconds):
    """Convert seconds to HH:MM:SS with leading zero."""
    total_seconds = int(round(total_seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def fetch_results(race_id):
    """Fetch all results for a race."""
    url = f"{API_BASE}/races/{race_id}/results"
    print(f"  Fetching {url} ...")
    resp = SESSION.get(url, timeout=300)
    resp.raise_for_status()
    return resp.json()


def process_race(race_info):
    """Fetch and process a single race."""
    label = f"{race_info['event']} {race_info['year']} ({race_info['distance']}, raceId={race_info['raceId']})"
    print(f"\n{'='*60}")
    print(f"Processing: {label}")

    results = fetch_results(race_info["raceId"])
    print(f"  Got {len(results)} raw results")

    distance = race_info["distance"]
    min_sec, max_sec = TIME_FILTERS[distance]

    # Use realTime first, fall back to officialTime
    valid_times = []
    men_winner = None
    women_winner = None

    for r in results:
        # Find winners by sexRanking
        sex = r.get("sex", "")
        sex_rank = r.get("sexRanking")
        t_str = r.get("realTime") or r.get("officialTime") or ""
        name = f"{r.get('firstName', '')} {r.get('lastName', '')}".strip()

        if sex_rank == 1 and sex == "M":
            if men_winner is None:
                men_winner = {"time": t_str, "name": name}
        if sex_rank == 1 and sex == "F":
            if women_winner is None:
                women_winner = {"time": t_str, "name": name}

        # Parse time for average computation
        secs = parse_time_to_seconds(t_str)
        if secs is not None and min_sec <= secs <= max_sec:
            valid_times.append(secs)

    finishers = len(results)
    avg_secs = sum(valid_times) / len(valid_times) if valid_times else 0
    avg_time_str = seconds_to_hhmmss(avg_secs) if valid_times else "N/A"
    dist_km = DISTANCE_KM[distance]
    avg_speed = dist_km / (avg_secs / 3600) if avg_secs > 0 else 0

    entry = {
        "event": race_info["event"],
        "distance": distance,
        "year": race_info["year"],
        "raceId": race_info["raceId"],
        "finishers": finishers,
        "valid_times_count": len(valid_times),
        "avg_time": avg_time_str,
        "avg_speed_kmh": round(avg_speed, 2),
        "men_winner_time": men_winner["time"] if men_winner else "N/A",
        "men_winner_name": men_winner["name"] if men_winner else "N/A",
        "women_winner_time": women_winner["time"] if women_winner else "N/A",
        "women_winner_name": women_winner["name"] if women_winner else "N/A",
    }

    # Format winner times with leading zeros
    for key in ["men_winner_time", "women_winner_time"]:
        secs = parse_time_to_seconds(entry[key])
        if secs is not None:
            entry[key] = seconds_to_hhmmss(secs)

    print(f"  Finishers: {finishers}")
    print(f"  Valid times for avg: {len(valid_times)}")
    print(f"  Avg time: {avg_time_str} ({avg_speed:.2f} km/h)")
    print(f"  Men winner: {entry['men_winner_name']} - {entry['men_winner_time']}")
    print(f"  Women winner: {entry['women_winner_name']} - {entry['women_winner_time']}")

    return entry


def main():
    all_results = []

    for race in RACES:
        try:
            entry = process_race(race)
            all_results.append(entry)
        except Exception as e:
            print(f"  ERROR: {e}")
            all_results.append({
                "event": race["event"],
                "distance": race["distance"],
                "year": race["year"],
                "raceId": race["raceId"],
                "error": str(e),
            })
        # Small delay between requests
        time_module.sleep(1)

    output_path = "C:/Users/mbrun/datapace-dashboard/timeto_4d_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Done! Saved {len(all_results)} race entries to {output_path}")


if __name__ == "__main__":
    main()
