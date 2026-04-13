#!/usr/bin/env python3
"""
Fetch Marathon de Paris 2026 results from TimeTo / SportInnovation API.

Outputs:
  - Winner times (men / women)
  - Average finish time (overall, men, women)
  - Top 10 nationalities
  - Top 3 first names (men / women)

Usage:
    python fetch_timeto_paris2026.py

Requires: requests (pip install requests)
"""
import requests
import json
import sys
from collections import Counter
from datetime import timedelta

BASE = "https://sportinnovation.fr/api"
SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})


def find_event():
    """Find the Marathon de Paris 2026 event ID."""
    resp = SESSION.get(f"{BASE}/events")
    resp.raise_for_status()
    events = resp.json()
    for ev in events:
        name = ev.get("name", "") or ev.get("title", "")
        if "paris" in name.lower() and ("marathon" in name.lower() or "schneider" in name.lower()):
            year = ev.get("year") or ev.get("date", "")[:4]
            if str(year) == "2026" or "2026" in str(ev.get("date", "")):
                print(f"Found event: {name} (id={ev['id']})")
                return ev
    # If not found by year filter, list all Paris marathon events
    print("Could not auto-detect 2026. Listing all Paris marathon events:")
    for ev in events:
        name = ev.get("name", "") or ev.get("title", "")
        if "paris" in name.lower() and "marathon" in name.lower():
            print(f"  id={ev.get('id')} name={name} date={ev.get('date', '?')}")
    return None


def get_races(event_id):
    """Get races for the event."""
    resp = SESSION.get(f"{BASE}/events/{event_id}/races")
    resp.raise_for_status()
    races = resp.json()
    print(f"\nRaces found: {len(races)}")
    for r in races:
        dist = r.get("distance", "?")
        name = r.get("name", "?")
        total = r.get("totals", {}).get("maxGeneralRanking", "?")
        print(f"  id={r['id']} name={name} distance={dist}m finishers={total}")
    return races


def find_marathon_race(races):
    """Find the 42K race among the races."""
    for r in races:
        dist = r.get("distance", 0)
        name = (r.get("name") or "").lower()
        if dist and 42000 <= int(dist) <= 42300:
            return r
        if "marathon" in name and "semi" not in name and "half" not in name:
            return r
    return None


def fetch_all_results(event_id, race_id):
    """Fetch all individual results with pagination."""
    all_results = []
    page = 1
    per_page = 500
    while True:
        url = f"{BASE}/events/{event_id}/races/{race_id}/results"
        params = {"page": page, "per_page": per_page}
        resp = SESSION.get(url, params=params)
        if resp.status_code != 200:
            print(f"  Page {page}: HTTP {resp.status_code}, stopping.")
            break
        data = resp.json()
        results = data if isinstance(data, list) else data.get("results", data.get("data", []))
        if not results:
            break
        all_results.extend(results)
        print(f"  Page {page}: {len(results)} results (total: {len(all_results)})")
        if len(results) < per_page:
            break
        page += 1
    return all_results


def parse_time_seconds(time_str):
    """Parse a time string like '4:12:34' or '04:12:34' to seconds."""
    if not time_str:
        return None
    parts = str(time_str).strip().split(":")
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = int(parts[0]), float(parts[1])
            return m * 60 + s
    except (ValueError, TypeError):
        return None
    return None


def seconds_to_hms(total_seconds):
    """Convert seconds to H:MM:SS string."""
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    return f"{h}:{m:02d}:{s:02d}"


def analyze_results(results):
    """Analyze all results and produce stats."""
    times_all = []
    times_men = []
    times_women = []
    names_men = []
    names_women = []
    nations = []

    for r in results:
        # Time: try various field names
        time_str = (r.get("time") or r.get("netTime") or r.get("chipTime")
                    or r.get("officialTime") or r.get("gunTime") or "")
        t = parse_time_seconds(time_str)
        if t and 7200 < t < 28800:  # Between 2h and 8h
            times_all.append(t)

            # Gender
            gender = (r.get("gender") or r.get("sex") or r.get("sexe") or "").upper()
            if gender in ("M", "H", "MALE", "HOMME"):
                times_men.append(t)
            elif gender in ("F", "W", "FEMALE", "FEMME"):
                times_women.append(t)

        # Name
        first_name = (r.get("firstName") or r.get("firstname") or
                      r.get("prenom") or r.get("first_name") or "").strip()
        gender = (r.get("gender") or r.get("sex") or r.get("sexe") or "").upper()
        if first_name:
            canonical = first_name.upper()
            if gender in ("M", "H", "MALE", "HOMME"):
                names_men.append(canonical)
            elif gender in ("F", "W", "FEMALE", "FEMME"):
                names_women.append(canonical)

        # Nationality
        nat = (r.get("nationality") or r.get("country") or
               r.get("countryCode") or r.get("pays") or "").strip().upper()
        if nat and len(nat) <= 5:
            nations.append(nat)

    print(f"\n{'='*60}")
    print(f"MARATHON DE PARIS 2026 - STATISTIQUES")
    print(f"{'='*60}")
    print(f"\nResultats analyses: {len(times_all)}")

    # Winners
    if times_all:
        print(f"\n--- VAINQUEURS ---")
        if times_men:
            print(f"  Homme: {seconds_to_hms(min(times_men))}")
        if times_women:
            print(f"  Femme: {seconds_to_hms(min(times_women))}")

    # Averages
    if times_all:
        avg_all = sum(times_all) / len(times_all)
        avg_speed = 42.195 / (avg_all / 3600)
        print(f"\n--- TEMPS MOYENS ---")
        print(f"  General: {seconds_to_hms(avg_all)} ({len(times_all)} finishers)")
        print(f"  Vitesse moyenne: {avg_speed:.2f} km/h")
        if times_men:
            avg_m = sum(times_men) / len(times_men)
            print(f"  Hommes:  {seconds_to_hms(avg_m)} ({len(times_men)} finishers)")
        if times_women:
            avg_f = sum(times_women) / len(times_women)
            print(f"  Femmes:  {seconds_to_hms(avg_f)} ({len(times_women)} finishers)")

    # Top nations
    if nations:
        print(f"\n--- TOP 10 NATIONS ---")
        for nat, count in Counter(nations).most_common(10):
            pct = count / len(nations) * 100
            print(f"  {nat:5s}: {count:6d} ({pct:.1f}%)")

    # Top first names
    if names_men:
        print(f"\n--- TOP 3 PRENOMS MASCULINS ---")
        for name, count in Counter(names_men).most_common(3):
            print(f"  {name}: {count}")
    if names_women:
        print(f"\n--- TOP 3 PRENOMS FEMININS ---")
        for name, count in Counter(names_women).most_common(3):
            print(f"  {name}: {count}")

    # Return avg time for dashboard update
    return {
        "avg_time": seconds_to_hms(avg_all) if times_all else None,
        "avg_speed_kmh": round(avg_speed, 2) if times_all else None,
        "count": len(times_all),
        "avg_men": seconds_to_hms(sum(times_men) / len(times_men)) if times_men else None,
        "avg_women": seconds_to_hms(sum(times_women) / len(times_women)) if times_women else None,
        "top_nations": Counter(nations).most_common(10) if nations else [],
        "top_names_men": Counter(names_men).most_common(3) if names_men else [],
        "top_names_women": Counter(names_women).most_common(3) if names_women else [],
    }


def update_avg_times_json(stats):
    """Add the 2026 avg time to avg_times_sporthive.json."""
    if not stats.get("avg_time"):
        print("\nPas de temps moyen a ajouter.")
        return
    with open("avg_times_sporthive.json") as f:
        data = json.load(f)
    # Remove existing 2026 entry if any
    data = [e for e in data if not (e.get("race") == "Schneider Electric Marathon de Paris" and e.get("year") == 2026)]
    data.append({
        "label": "Marathon de Paris 2026",
        "race": "Schneider Electric Marathon de Paris",
        "dist_m": 42195,
        "year": 2026,
        "count": stats["count"],
        "avg_time": stats["avg_time"],
        "avg_speed_kmh": stats["avg_speed_kmh"]
    })
    with open("avg_times_sporthive.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\navg_times_sporthive.json mis a jour avec Marathon de Paris 2026: {stats['avg_time']}")


def main():
    print("Recherche de l'evenement Marathon de Paris 2026...")
    event = find_event()
    if not event:
        print("Evenement non trouve. Veuillez verifier l'API.")
        sys.exit(1)

    event_id = event["id"]
    races = get_races(event_id)
    marathon_race = find_marathon_race(races)
    if not marathon_race:
        print("Course marathon (42K) non trouvee parmi les races.")
        sys.exit(1)

    race_id = marathon_race["id"]
    print(f"\nTelechargement des resultats pour: {marathon_race.get('name', '?')} (id={race_id})...")
    results = fetch_all_results(event_id, race_id)
    if not results:
        print("Aucun resultat telecharge.")
        # Show sample result structure
        print("Trying alternative result endpoints...")
        # Try rankings endpoint
        try:
            resp = SESSION.get(f"{BASE}/events/{event_id}/races/{race_id}/rankings")
            if resp.ok:
                rankings = resp.json()
                print(f"Rankings found: {len(rankings) if isinstance(rankings, list) else 'dict'}")
                if isinstance(rankings, list) and rankings:
                    # Try first ranking
                    rank_id = rankings[0].get("id")
                    resp2 = SESSION.get(f"{BASE}/events/{event_id}/races/{race_id}/rankings/{rank_id}/results",
                                        params={"page": 1, "per_page": 5})
                    if resp2.ok:
                        sample = resp2.json()
                        print(f"Sample: {json.dumps(sample[:2] if isinstance(sample, list) else sample, indent=2)[:1000]}")
        except Exception as e:
            print(f"Error: {e}")
        sys.exit(1)

    # Show first result structure for debugging
    print(f"\nSample result structure:")
    print(json.dumps(results[0], indent=2, ensure_ascii=False)[:500])

    stats = analyze_results(results)

    # Save stats
    with open("paris_marathon_2026_stats.json", "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\nStats sauvegardees dans paris_marathon_2026_stats.json")

    # Update avg_times_sporthive.json
    update_avg_times_json(stats)


if __name__ == "__main__":
    main()
